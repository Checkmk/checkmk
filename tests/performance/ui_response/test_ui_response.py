#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Performance: how long a page of the GUI takes to load."""

from collections.abc import Iterator
from functools import partial

import pytest
from playwright.sync_api import BrowserContext
from pytest_benchmark.fixture import BenchmarkFixture

from tests.performance.perftest import PerformanceTest
from tests.performance.ui_response import scenario
from tests.performance.ui_response.scenario import CmkPageUrl
from tests.testlib.common.repo import repo_path

#: A data row of the shared monitoring table. Its rows are virtualized, so only the ones on
#: screen exist in the DOM — the first one appearing is what "the table is up" means.
MONITORING_TABLE_ROW = "tr.monitoring-table__row[data-index]"

#: Deliberately loose. These are the first figures anyone has for the monitoring pages, and
#: the first runs are for learning what they are rather than policing a threshold nobody has
#: agreed. Tighten once a baseline exists.
MONITORING_PAGE_MAX_SECONDS = 30.0

#: The dummy agent dump generator, under the name it is copied into the site as. Named for
#: this module so a copy left behind by a crashed run says where it came from.
AGENT_DUMP_GENERATOR = "ui_response_dump_generator.py"


@pytest.fixture(name="monitored_host", scope="module")
def _monitored_host(perftest: PerformanceTest) -> Iterator[str]:
    """One host with its services discovered, for pages that must address a real object.

    The Services-of-a-host page lists the services of one named host, so pointing it at a
    host that does not exist would time an error page and report it as a page-load figure.
    The generated hosts of the other scenarios cannot be relied on: their bulk discovery
    belongs to a scenario of its own, so whether any of them has services depends on what
    ran first. This makes its own.

    The services come from a datasource program, not from an agent. Nothing listens on port
    6556 of a CI runner, so a host tagged ``cmk-agent`` at a loopback address discovers
    nothing there at all; the dump generator is what makes the discovery real, and it is the
    one the DCD scenario already stages its piggyback data with. The rule is scoped to this
    host alone, because the other scenarios' hosts share the site and a datasource program
    matching them too would change what they measure.

    ``--object-count`` sizes the services, as it sizes the estate elsewhere: this is the page
    that scales with one host's service count, so that is the axis the knob has to reach.
    """
    site = perftest.central_site
    hosts = perftest.generate_hosts(1, site, host_ip_offset=90000)
    hostname = str(hosts[0]["host_name"])

    site.write_file(
        AGENT_DUMP_GENERATOR,
        (repo_path() / "tests/scripts/dummy_agent_dump_generator.py").read_text(),
    )
    rule_id = site.openapi.rules.create(
        ruleset_name="datasource_programs",
        value=(
            f"python3 ~/{AGENT_DUMP_GENERATOR}"
            f" --host-name {hostname} --service-count {perftest.object_count}"
        ),
        conditions={"host_name": {"match_on": [hostname], "operator": "one_of"}},
    )
    try:
        # Creating the host activates, so the rule is in place by the time it is discovered.
        perftest.discover_services(site, perftest.create_hosts(site, hosts))
        perftest.monitored_host = hostname
        yield hostname
    finally:
        perftest.monitored_host = "dummy"
        if site.openapi.hosts.get(hostname):
            perftest.delete_hosts(site, [hostname])
        if site.openapi.rules.get(rule_id):
            site.openapi.rules.delete(rule_id)
            site.openapi.changes.activate_and_wait_for_completion()
        site.delete_file(AGENT_DUMP_GENERATOR)


@pytest.mark.parametrize(
    "page_url",
    [
        CmkPageUrl("login", "login.py", login=False),
        CmkPageUrl("edit_host", "wato.py?folder={folder}&host={host}&mode=edit_host"),
        CmkPageUrl("service_discovery", "wato.py?folder={folder}&host={host}&mode=inventory"),
        CmkPageUrl(
            "host_parameters",
            "wato.py?folder={folder}&host={host}&mode=object_parameters",
        ),
        # The two experimental monitoring pages. Both are Vue apps whose table arrives in a
        # request made after the document completes, so both name the row selector that says
        # the table is actually up — without it they would be timed to their own shell.
        # All hosts is the one that scales with --object-count: it lists every host there is.
        CmkPageUrl(
            "monitor_all_hosts",
            "monitor_all_hosts.py",
            wait_for_selector=MONITORING_TABLE_ROW,
            max_average_duration=MONITORING_PAGE_MAX_SECONDS,
        ),
        # Services of a host scales on the other axis — one host's services, not the estate.
        CmkPageUrl(
            "monitor_host_services",
            "monitor_host_services.py?host={monitored_host}&site={site}",
            wait_for_selector=MONITORING_TABLE_ROW,
            max_average_duration=MONITORING_PAGE_MAX_SECONDS,
        ),
        # The classic views the two pages above replace, measured the same way so the pair can
        # be compared. A classic view is server-rendered, so its table is in the document and
        # `domcontentloaded` is the whole story; naming a row selector would only add the wait
        # for an element that is already there.
        CmkPageUrl(
            "view_all_hosts",
            "view.py?view_name=allhosts",
            max_average_duration=MONITORING_PAGE_MAX_SECONDS,
        ),
        CmkPageUrl(
            "view_host_services",
            "view.py?view_name=host&host={monitored_host}&site={site}",
            max_average_duration=MONITORING_PAGE_MAX_SECONDS,
        ),
    ],
    ids=lambda url: url.id,
)
@pytest.mark.usefixtures("track_system_resources", "monitored_host")
def test_performance_ui_response(
    perftest: PerformanceTest,
    benchmark: BenchmarkFixture,
    page_url: CmkPageUrl,
    context: BrowserContext,
) -> None:
    print(f"Checking {page_url.value}...")  # noqa: T201  # It's OK for test/script helpers to print()
    benchmark.pedantic(  # type: ignore[no-untyped-call]
        partial(scenario.scenario_performance_ui_response, perftest),
        args=[context, page_url],
        rounds=perftest.rounds,
        iterations=perftest.iterations,
    )
