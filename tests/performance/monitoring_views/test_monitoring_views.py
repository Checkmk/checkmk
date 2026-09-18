#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# ruff: noqa: ARG001  # Unused fixtures are needed for setup side effects

"""The monitoring-page comparison against a real central site.

The in-process suite (``tests/performance/monitoring_views/in_process``) answers the same question far more
cheaply and at far greater width, and it is the one to reach for while investigating. This one
exists because that suite replaces the socket: it proves nothing about Apache, mod_wsgi, the
session handling, response compression or a real site's configuration. So the same scenarios are
run once more through a site that actually exists.

One real central site reads from Livestatus endpoints this module serves itself, configured as
ordinary status-only connections. Everything the central site does is real; the remotes are
generated data, which is what makes the number of remotes a knob rather than a procurement
decision.

That the remotes are faked costs nothing in fidelity: measured against two real remote sites of
the same size, the central site spent the same seconds, the same CPU (7.1s against 7.2s) and the
same resident memory (2730 MiB against 2733). The measurement is recorded outside this repo, in
the initiative's notes; it is not carried here as a test, because it answers a question that was
asked once rather than a property that regresses.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Iterator, Sequence
from contextlib import ExitStack
from dataclasses import dataclass
from time import time
from typing import Literal
from urllib.parse import urljoin

import pytest
import requests
from pytest_benchmark.fixture import BenchmarkFixture
from requests.auth import HTTPBasicAuth

from tests.performance.monitoring_views.livestatus_fake import (
    EstateShape,
    FakeSite,
    FakeVersion,
    QueryLog,
)
from tests.performance.monitoring_views.remotes import serve_remotes, ServedFleet
from tests.performance.monitoring_views.report import Measurement, Report
from tests.performance.monitoring_views.scenarios import (
    API_ROOT,
    Page,
    PageContext,
    PAGES,
)
from tests.performance.sysmon import get_process_group_usage
from tests.testlib.site import ADMIN_USER, Site

logger = logging.getLogger(__name__)

#: Where the GUI keeps its site connections. Written wholesale, so the central site's own entry
#: has to be written along with the fakes or the GUI loses track of itself.
_SITES_MK = "etc/check_mk/multisite.d/sites.mk"

#: Where the Livestatus proxy keeps its own copy of where the sites are. Setup writes it
#: alongside `sites.mk`; writing `sites.mk` directly means writing this one too, or the proxy
#: offers no socket for a site the GUI has been told to reach through it.
_LIVEPROXYD_MK = "etc/check_mk/liveproxyd.mk"

#: Filled as the measurements run; the conftest prints it once the run is over. A test
#: module is not a plugin, so the hook that renders it cannot live here.
REPORT = Report()


@dataclass(frozen=True, kw_only=True)
class SiteProbe:
    """Issues a page's requests against a real site over HTTP."""

    session: requests.Session
    base_url: str
    context: PageContext

    def run(self, requests_: object) -> None:
        requests_(self._call, self.context)  # type: ignore[operator]

    def _call(self, method: Literal["get", "post"], url: str, *, body: str | None = None) -> None:
        target = urljoin(self.base_url, url.removeprefix(self.context.site_prefix).lstrip("/"))
        response = (
            self.session.get(target, timeout=120)
            if method == "get"
            else self.session.post(
                target,
                data=body,
                timeout=120,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )
        )
        assert response.status_code == 200, (
            f"{method.upper()} {target} -> {response.status_code}: {response.text[:400]}"
        )


def _authenticated_session(site: Site) -> requests.Session:
    """A session carrying the GUI's auth cookie.

    The pages are measured the way a browser reaches them - one logged-in session reused across
    requests - rather than with per-request basic auth, which would put a login into every
    measurement.
    """
    session = requests.session()
    session.get(urljoin(site.url, "login.py"), auth=HTTPBasicAuth(ADMIN_USER, site.admin_password))
    assert any(cookie.name == f"auth_{site.id}" for cookie in session.cookies), (
        f"could not log in to site {site.id!r}"
    )
    return session


# .
#   .--fleet-----------------------------------------------------------------


@pytest.fixture(name="fake_remote_shape", scope="module")
def _fake_remote_shape(pytestconfig: pytest.Config) -> EstateShape:
    return EstateShape(
        hosts=int(pytestconfig.getoption("fake_remote_hosts")),
        services_per_host=20,
    )


@pytest.fixture(name="monitoring_fleet", scope="module")
def _monitoring_fleet(
    central_site: Site,
    pytestconfig: pytest.Config,
    fake_remote_shape: EstateShape,
) -> Iterator[Sequence[str]]:
    """Point the central site at a fleet of served fake remotes, and clean up after.

    Yields the site IDs in the fleet. With ``--fake-remotes=0`` nothing is served or written and
    the site keeps whatever connections it already has, which is how the real-remote mode runs.
    """
    remote_count = int(pytestconfig.getoption("fake_remotes"))
    latency = float(pytestconfig.getoption("fake_remote_latency_ms")) / 1000.0
    version = _version_of(central_site)
    log = QueryLog()
    fakes = [
        FakeSite(
            f"remote{index:02d}",
            fake_remote_shape,
            version=version,
            log=log,
            latency=latency,
        )
        for index in range(remote_count)
    ]

    via_proxy = bool(pytestconfig.getoption("fake_remote_proxy"))
    previous = _current(central_site, _SITES_MK)
    previous_proxy = _current(central_site, _LIVEPROXYD_MK)

    with ExitStack() as stack:
        fleet = stack.enter_context(serve_remotes(fakes))
        central_site.write_file(
            _SITES_MK, _sites_mk(central_site, fakes, fleet, via_proxy=via_proxy)
        )
        stack.callback(_restore_file, central_site, _SITES_MK, previous)
        if via_proxy:
            central_site.write_file(_LIVEPROXYD_MK, _liveproxyd_mk(fakes, fleet))
            stack.callback(_restore_file, central_site, _LIVEPROXYD_MK, previous_proxy)
        # The GUI reads its site connections from configuration loaded per request, but the
        # workers cache more than that; restarting Apache is the blunt way to be sure the
        # fleet is what the next request sees. The proxy only reads its own file at startup.
        _restart(central_site, via_proxy=via_proxy)
        try:
            yield [central_site.id, *(fake.site_id for fake in fakes)]
        finally:
            _restart(central_site, via_proxy=via_proxy)


def _current(site: Site, path: str) -> str | None:
    return site.read_file(path) if site.file_exists(path) else None


#: What the Livestatus proxy writes about itself. Debug logging is already turned on for it
#: when a commercial-edition test site is created, so this is where to look when the GUI is
#: told to read through the proxy and sees nothing.
_LIVEPROXYD_LOG = "var/log/liveproxyd.log"


def _restart(site: Site, *, via_proxy: bool) -> None:
    if via_proxy:
        # Turns the daemon on if it is off and asserts it came up, rather than restarting a
        # service that may not be enabled at all - `omd restart` on a disabled one succeeds
        # quietly, and the first sign of trouble would then be a fleet holding no hosts.
        site.toggle_liveproxyd(True)
        site.omd("restart", "liveproxyd", check=True)
    site.omd("restart", "apache", check=True)


def _proxy_diagnostics(site: Site) -> str:
    """The tail of the proxy's own log, for when it is between the GUI and the sites."""
    if not site.file_exists(_LIVEPROXYD_LOG):
        return f"({_LIVEPROXYD_LOG} does not exist)"
    return "\n".join(site.read_file(_LIVEPROXYD_LOG).splitlines()[-40:])


def _restore_file(site: Site, path: str, previous: str | None) -> None:
    if previous is None:
        if site.file_exists(path):
            site.delete_file(path)
    else:
        site.write_file(path, previous)


def _restore_sites_mk(site: Site, previous: str | None) -> None:
    _restore_file(site, _SITES_MK, previous)


def _liveproxyd_mk(fakes: Sequence[FakeSite], fleet: ServedFleet) -> str:
    """Where the proxy should connect for each site, in the shape Setup writes."""
    entries = {fake.site_id: {"socket": fleet.socket_spec(fake.site_id)} for fake in fakes}
    return f"sites = locals().setdefault('sites', {{}})\nsites.update({entries!r})\n"


def _version_of(site: Site) -> FakeVersion:
    """What the fakes must claim to be to be accepted as remotes of this central site.

    A site whose version or edition the central cannot place is dropped from every query rather
    than reported as broken, so getting this wrong makes the whole fleet quietly disappear.
    """
    return FakeVersion(
        livestatus_version=site.version.version,
        program_version=f"Check_MK {site.version.version}",
        edition=site.edition.long,
    )


def _sites_mk(
    central: Site, fakes: Sequence[FakeSite], fleet: ServedFleet, *, via_proxy: bool = False
) -> str:
    """The site connections: the central site itself, plus one status-only entry per fake.

    ``via_proxy`` routes the remotes through the Livestatus proxy, which is how the
    commercial editions reach a distributed setup: the GUI then talks to a local unix socket
    the proxy owns, and the proxy holds the connections to the sites and answers some of the
    traffic from its own cache. That is a different distributed read path, not a faster one,
    and a comparison of round trips means something different behind it.
    """
    entries: dict[str, dict[str, object]] = {
        central.id: {
            "id": central.id,
            "alias": "Local site",
            "socket": ("local", None),
            "proxy": None,
            "replication": None,
            "disabled": False,
            "disable_wato": True,
            "insecure": False,
            "multisiteurl": "",
            "persist": False,
            "replicate_ec": False,
            "replicate_mkps": False,
            "message_broker_port": 5672,
            "status_host": None,
            "timeout": 10,
            "url_prefix": f"/{central.id}/",
            "user_login": True,
            "is_trusted": False,
        }
    }
    for fake in fakes:
        entries[fake.site_id] = {
            **entries[central.id],
            "id": fake.site_id,
            "alias": f"Fake remote {fake.site_id}",
            "socket": fleet.socket_spec(fake.site_id),
            "url_prefix": f"/{fake.site_id}/",
            # `params: None` means "use the globally configured proxy parameters", which is the
            # default a site connection is created with.
            "proxy": {"params": None} if via_proxy else None,
        }
    # The exact shape `cmk.ccc.store.save_to_mk_file` writes: the variable is bootstrapped into
    # the exec's locals first, because the file is loaded against an empty default.
    return f"sites = locals().setdefault('sites', {{}})\nsites.update({entries!r})\n"


@pytest.fixture(name="site_probe", scope="module")
def _site_probe(
    central_site: Site,
    monitoring_fleet: Sequence[str],
    fake_remote_shape: EstateShape,
    pytestconfig: pytest.Config,
) -> SiteProbe:
    """A probe pointed at a host one of the faked remotes holds."""
    remote_count = int(pytestconfig.getoption("fake_remotes"))
    host_site = monitoring_fleet[1]

    session = _authenticated_session(central_site)
    _assert_fleet_is_being_read(
        session,
        central_site.url,
        expected_hosts=remote_count * fake_remote_shape.hosts,
        diagnostics=lambda: (
            _proxy_diagnostics(central_site) if pytestconfig.getoption("fake_remote_proxy") else ""
        ),
    )

    return SiteProbe(
        session=session,
        base_url=central_site.url,
        context=PageContext(
            site_prefix=f"/{central_site.id}/check_mk",
            limit=pytestconfig.getoption("row_limit_real"),
            host_name=f"{host_site}-host-000000",
            host_site_id=host_site,
        ),
    )


def _assert_fleet_is_being_read(
    session: requests.Session,
    base_url: str,
    *,
    expected_hosts: int,
    diagnostics: Callable[[], str] = lambda: "",
) -> None:
    """Prove the central site is really reading the fake remotes before anything is timed.

    A remote whose version or edition the central cannot place is dropped from every query
    rather than reported as broken, and so is one whose connection was never configured. Either
    way the pages still render, still return 200, and are measured against an estate that is not
    there - fast, and meaningless. The estate-wide total the listing endpoint returns is the
    cheapest thing that can only be right if every site is answering.
    """
    response = session.post(
        urljoin(base_url, f"{API_ROOT}/monitor/hosts"),
        data=json.dumps({"limit": 1}),
        timeout=120,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    assert response.status_code == 200, f"could not read the fleet: {response.text[:400]}"

    total = int(response.json()["meta"]["total"])
    logger.info("The central site sees %d hosts across the fleet", total)
    assert total >= expected_hosts, (
        f"the fleet should hold at least {expected_hosts} hosts but the central site sees "
        f"{total}; the faked remotes are configured but not being read.\n{diagnostics()}"
    )


# .
#   .--measurements-----------------------------------------------------------


@pytest.mark.parametrize("page", PAGES, ids=lambda page: page.id)
def test_monitoring_page_load(
    benchmark: BenchmarkFixture,
    central_site: Site,
    site_probe: SiteProbe,
    monitoring_fleet: Sequence[str],
    fake_remote_shape: EstateShape,
    track_system_resources: None,
    page: Page,
) -> None:
    """Time a first page load of each page against a real site."""
    _measure(benchmark, site_probe, page, "load", monitoring_fleet, fake_remote_shape, central_site)


@pytest.mark.parametrize("page", PAGES, ids=lambda page: page.id)
def test_monitoring_page_refresh(
    benchmark: BenchmarkFixture,
    central_site: Site,
    site_probe: SiteProbe,
    monitoring_fleet: Sequence[str],
    fake_remote_shape: EstateShape,
    track_system_resources: None,
    page: Page,
) -> None:
    """Time what the page repeats on its refresh timer, which is what an open tab costs."""
    _measure(
        benchmark, site_probe, page, "refresh", monitoring_fleet, fake_remote_shape, central_site
    )


def _measure(
    benchmark: BenchmarkFixture,
    probe: SiteProbe,
    page: Page,
    phase: str,
    fleet: Sequence[str],
    shape: EstateShape,
    site: Site,
) -> None:
    requests_ = page.load if phase == "load" else page.poll
    started = time()
    # Sampled around the rounds rather than machine-wide: this process serves the faked
    # remotes, so only the site's own processes say what the *site* spent.
    before = get_process_group_usage(site.id)
    benchmark.pedantic(  # type: ignore[no-untyped-call]
        probe.run,
        args=[requests_],
        rounds=5,
        iterations=1,
        warmup_rounds=1,
    )
    after = get_process_group_usage(site.id)
    logger.info(
        "%s %s took %.3fs in total, %.1fs of it the site's own cpu",
        page.id,
        phase,
        time() - started,
        after.cpu_seconds - before.cpu_seconds,
    )
    REPORT.add(
        Measurement(
            scenario="real site",
            page=page.id,
            phase=phase,
            sites=len(fleet),
            hosts_per_site=shape.hosts,
            # Only the fake fleet can count what a site was asked; against real remotes these
            # stay at zero and the table reports seconds alone.
            queries=0,
            fan_outs=0.0,
            rows=0,
            payload_bytes=0,
            queries_by_kind={},
            seconds=_mean_seconds(benchmark),
            cpu_seconds=after.cpu_seconds - before.cpu_seconds,
            rss_mib=max(before.rss_mib, after.rss_mib),
        )
    )


def _mean_seconds(benchmark: BenchmarkFixture) -> float | None:
    """The mean of the rounds just measured, or nothing if the run was interrupted."""
    stats = getattr(benchmark, "stats", None)
    return None if stats is None else float(stats.stats.mean)
