#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Fixtures for comparing the new monitoring pages with the views they replace.

The GUI runs in this process against a fleet of fake Livestatus sites (see
:mod:`.livestatus_fake`), which is what lets a fifty-remote scenario run without a single OMD
site. The fixture stack below is the one the REST-API suite uses, trimmed to what a page load
needs, plus the fleet itself.
"""

# mypy: disable-error-code="explicit-any"
# mypy: disable-error-code="no-untyped-def"

from __future__ import annotations

import logging
import os
import queue
from collections.abc import Callable, Generator, Iterator
from typing import override
from contextlib import contextmanager

import pytest

import cmk.ccc.version as cmk_version

# NOTE: fake_paths must run BEFORE any cmk.gui import. Modules like cmk/gui/userdb/store.py
# capture `cmk.utils.paths.var_dir` at import time; patching afterwards is too late.
pytest.register_assert_rewrite("tests.testlib")


from tests.testlib import fake_site  # noqa: E402

fake_site.fake_paths()


from flask import Flask  # noqa: E402
from pytest_mock import MockerFixture  # noqa: E402

from cmk.ccc.site import SiteId  # noqa: E402
from cmk.ccc.user import UserId  # noqa: E402
from cmk.gui.config import Config  # noqa: E402
from cmk.licensing.handler import (  # noqa: E402
    LicenseState,
    LicensingHandler,
    NotificationHandler,
    UserEffect,
)
from tests.performance.monitoring_views.in_process.fleet import (  # noqa: E402
    CENTRAL_SITE_ID,
    FleetBuilder,
    site_configurations,
)
from tests.performance.monitoring_views.livestatus_fake import (  # noqa: E402
    EstateShape,
    FakeVersion,
    QueryLog,
)
from tests.performance.monitoring_views.in_process.components import (  # noqa: E402
    ComponentProfile,
    profile_lines,
)
from tests.performance.monitoring_views.report import Report  # noqa: E402
from tests.performance.monitoring_views.scenarios import LimitTier, TIERS  # noqa: E402
from tests.performance.monitoring_views.remotes import (  # noqa: E402
    build_sites,
    patched_remotes,
)
from tests.testlib.gui.common_fixtures import (  # noqa: E402
    create_flask_app,
    create_wsgi_app,
    perform_gui_cleanup_after_test,
    perform_load_config,
    patch_theme_context,
    perform_load_plugins,
    set_config_context,
    validate_background_job_annotation,
)
from tests.testlib.gui.users import create_and_destroy_user  # noqa: E402
from tests.testlib.gui.web_test_app import SetConfig, WebTestAppForCMK  # noqa: E402

logger = logging.getLogger(__name__)


class _DummyNotificationHandler(NotificationHandler):
    @override
    def manage_notification(self) -> None:
        pass


class _DummyLicensingHandler(LicensingHandler):
    """A licence that never expires, so no page spends time deciding whether to say so."""

    @classmethod
    @override
    def make(cls) -> _DummyLicensingHandler:
        return cls()

    @property
    @override
    def state(self) -> LicenseState:
        return LicenseState.LICENSED

    @property
    @override
    def message(self) -> str:
        return ""

    @override
    def effect_core(self, num_services: int, num_hosts_shadow: int) -> UserEffect:
        return UserEffect(header=None, email=None, block=None)

    @override
    def effect(self, licensing_settings_link: str | None = None) -> UserEffect:
        return UserEffect(header=None, email=None, block=None)

    @property
    @override
    def notification_handler(self) -> NotificationHandler:
        return _DummyNotificationHandler(email_notification=None)


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("monitoring view performance")
    group.addoption(
        "--remote-sites",
        action="store",
        type=int,
        default=20,
        help="Number of fake remote sites the central site reads from.",
    )
    group.addoption(
        "--hosts-per-site",
        action="store",
        type=int,
        default=500,
        help="Number of hosts each site in the fleet monitors.",
    )
    group.addoption(
        "--services-per-host",
        action="store",
        type=int,
        default=20,
        help="Number of services each generated host has.",
    )
    group.addoption(
        "--remote-latency-ms",
        action="store",
        type=float,
        default=0.0,
        help=(
            "Delay every fake site adds before answering, in milliseconds. Zero measures the "
            "central site alone; a WAN-like value makes the number of round trips a page takes "
            "visible in the result."
        ),
    )
    group.addoption(
        "--row-limit",
        action="store",
        choices=TIERS,
        default="soft",
        help=(
            "Which row limit both pages are measured at: 'soft' (1000 rows, the default either "
            "offers), 'hard' (5000) or 'none' (no limit). Asking for more rows is how these "
            "pages load additional entries - neither fetches more as you scroll."
        ),
    )


# .
#   .--environment-----------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def cleanup_cmk() -> Generator[None]:
    yield from fake_site.cleanup_cmk_tmp_dir()


@pytest.fixture(autouse=True, scope="session")
def fixture_umask() -> Generator[None]:
    old_mask = os.umask(0o0007)
    try:
        yield
    finally:
        os.umask(old_mask)


@pytest.fixture(autouse=True, scope="session")
def fixture_omd_site() -> Generator[None]:
    os.environ["OMD_SITE"] = CENTRAL_SITE_ID
    yield


@pytest.fixture(autouse=True)
def cleanup_after_test() -> Generator[None]:
    yield from fake_site.cleanup_omd_root_after_test()


@pytest.fixture(autouse=True, scope="session")
def reduce_password_hashing_rounds() -> Iterator[None]:
    yield from fake_site.reduce_password_hashing_rounds()


@pytest.fixture(autouse=True, scope="session")
def prevent_security_event_file_logging() -> Iterator[queue.Queue[logging.LogRecord]]:
    yield from fake_site.prevent_security_event_file_logging()


@pytest.fixture(scope="session")
def test_edition() -> cmk_version.Edition:
    return fake_site.edition()


@pytest.fixture(scope="session", autouse=True)
def patch_omd_version(test_edition: cmk_version.Edition) -> Iterator[None]:
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(cmk_version, "orig_omd_version", cmk_version.omd_version, raising=False)
        mp.setattr(
            cmk_version,
            "omd_version",
            lambda *args, **kw: f"{cmk_version.__version__}.{test_edition.long}",
        )
        cmk_version.edition.cache_clear()
        yield


@pytest.fixture
def patch_omd_site(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    yield from fake_site.setup_fake_omd_site(monkeypatch)


@pytest.fixture(scope="module")
def use_fakeredis_client() -> Iterator[None]:
    yield from fake_site.use_fakeredis()


@pytest.fixture(scope="session", autouse=True)
def load_plugins(test_edition: cmk_version.Edition) -> None:
    perform_load_plugins(test_edition)


@pytest.fixture(autouse=True)
def disable_automation_helper(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("_CMK_AUTOMATIONS_FORCE_CLI_INTERFACE", "1")


@pytest.fixture(autouse=True)
def execute_background_jobs_without_job_scheduler(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("_CMK_BG_JOBS_WITHOUT_JOB_SCHEDULER", "1")


@pytest.fixture(autouse=True)
def gui_cleanup_after_test(mocker: MockerFixture) -> Iterator[None]:
    yield from perform_gui_cleanup_after_test(mocker)


@pytest.fixture(autouse=True)
def fail_on_unannotated_background_job_start(
    request: pytest.FixtureRequest, mocker: MockerFixture
) -> None:
    validate_background_job_annotation(request, mocker)


# .
#   .--gui-------------------------------------------------------------------


@pytest.fixture(name="monkeypatch_module", scope="module")
def fixture_monkeypatch_module() -> Iterator[pytest.MonkeyPatch]:
    with pytest.MonkeyPatch.context() as mp:
        yield mp


@pytest.fixture(name="quiesce_licensing", scope="module")
def fixture_quiesce_licensing(monkeypatch_module: pytest.MonkeyPatch) -> None:
    """Take licensing out of the comparison.

    Both generations render the same page header, so a licence banner would cost both the same
    - but it can reach out to files and state that have nothing to do with reading hosts, and
    that noise lands in the measurement.
    """
    monkeypatch_module.setattr(
        "cmk.licensing.registry._get_licensing_handler_factory",
        lambda omd_root: _DummyLicensingHandler.make,
    )
    monkeypatch_module.setattr("cmk.gui.top_heading.show_license_expiry", lambda x, y: None)
    monkeypatch_module.setattr("cmk.gui.top_heading.show_license_banner", lambda x, y: None)


@pytest.fixture(name="patch_theme")
def fixture_patch_theme() -> Iterator[None]:
    yield from patch_theme_context()


@pytest.fixture()
def flask_app(
    patch_omd_site: None,
    use_fakeredis_client: None,
    load_plugins: None,
) -> Iterator[Flask]:
    yield from create_flask_app()


@pytest.fixture()
def request_context(flask_app: Flask) -> Iterator[None]:
    """Empty fixture. Invokes usage of the `flask_app` fixture."""
    yield


@pytest.fixture()
def load_config(request_context: None) -> Iterator[Config]:
    yield from perform_load_config()


@pytest.fixture(name="set_config")
def set_config_fixture() -> SetConfig:
    return set_config_context


@pytest.fixture()
def with_admin(load_config: Config) -> Iterator[tuple[UserId, str]]:
    with create_and_destroy_user(automation=False, role="admin", config=load_config) as user:
        yield user


@pytest.fixture()
def wsgi_app(flask_app: Flask) -> Iterator[WebTestAppForCMK]:
    yield from create_wsgi_app(flask_app)


@pytest.fixture()
def logged_in_admin_wsgi_app(
    wsgi_app: WebTestAppForCMK, with_admin: tuple[UserId, str]
) -> WebTestAppForCMK:
    """An admin session.

    Admin rather than a restricted user on purpose: a user without "see all" makes Livestatus
    apply an ``AuthUser`` filter, which changes how much each site has to scan and would put a
    second variable into a comparison that is about the GUI.
    """
    _ = wsgi_app.login(with_admin[0], with_admin[1])
    return wsgi_app


# .
#   .--fleet-----------------------------------------------------------------


@pytest.fixture(name="fleet_shape")
def fixture_fleet_shape(pytestconfig: pytest.Config) -> EstateShape:
    return EstateShape(
        hosts=int(pytestconfig.getoption("hosts_per_site")),
        services_per_host=int(pytestconfig.getoption("services_per_host")),
    )


@pytest.fixture(name="remote_count")
def fixture_remote_count(pytestconfig: pytest.Config) -> int:
    return int(pytestconfig.getoption("remote_sites"))


@pytest.fixture(name="limit_tier")
def fixture_limit_tier(pytestconfig: pytest.Config) -> LimitTier:
    tier: LimitTier = pytestconfig.getoption("row_limit")
    return tier


@pytest.fixture(name="remote_latency")
def fixture_remote_latency(pytestconfig: pytest.Config) -> float:
    return float(pytestconfig.getoption("remote_latency_ms")) / 1000.0


@pytest.fixture(name="fake_version")
def fixture_fake_version(test_edition: cmk_version.Edition) -> FakeVersion:
    """What every fake site claims to be: this build, this edition.

    A site whose version or edition the central cannot place is dropped from the connection
    entirely, so the fleet would silently shrink to nothing and every page would look fast.
    """
    return FakeVersion(
        livestatus_version=cmk_version.__version__,
        program_version=f"Check_MK {cmk_version.__version__}",
        edition=test_edition.long,
    )


#: One report per run, so every measurement lands in the same table however the tests are
#: sliced up by parametrisation.
_REPORT = Report()

#: Where each profiled page load spent its time. Kept beside the comparison because the two
#: answer different questions: the table says which page is dearer, this says what it is paying
#: for - and whether the fake fleet is a large enough part of that to distrust the rest.
_PROFILES: list[ComponentProfile] = []


@pytest.fixture(name="report", scope="session")
def fixture_report() -> Report:
    return _REPORT


@pytest.fixture(name="profiles", scope="session")
def fixture_profiles() -> list[ComponentProfile]:
    return _PROFILES


def pytest_terminal_summary(terminalreporter: pytest.TerminalReporter) -> None:
    if lines := _REPORT.lines():
        terminalreporter.write_sep("=", "monitoring page comparison")
        for line in lines:
            terminalreporter.write_line(line)

    if lines := profile_lines(_PROFILES):
        terminalreporter.write_sep("=", "where a page load spends its time")
        for line in lines:
            terminalreporter.write_line(line)


@pytest.fixture(name="query_log")
def fixture_query_log() -> QueryLog:
    return QueryLog()


@pytest.fixture(name="fake_fleet")
def fixture_fake_fleet(
    remote_count: int,
    fleet_shape: EstateShape,
    fake_version: FakeVersion,
    remote_latency: float,
    query_log: QueryLog,
    set_config: SetConfig,
    logged_in_admin_wsgi_app: WebTestAppForCMK,
    quiesce_licensing: None,
    patch_theme: None,
) -> Iterator[WebTestAppForCMK]:
    """A logged-in GUI whose configured sites are all answered by the fake fleet."""
    sites = build_sites(
        central_site_id=CENTRAL_SITE_ID,
        remote_count=remote_count,
        shape=fleet_shape,
        version=fake_version,
        log=query_log,
        latency=remote_latency,
    )
    with (
        set_config(sites=site_configurations([SiteId(site_id) for site_id in sites])),
        patched_remotes(sites),
    ):
        yield logged_in_admin_wsgi_app


@pytest.fixture(name="fleet_builder")
def fixture_fleet_builder(
    fake_version: FakeVersion,
    remote_latency: float,
    set_config: SetConfig,
    logged_in_admin_wsgi_app: WebTestAppForCMK,
    quiesce_licensing: None,
    patch_theme: None,
) -> FleetBuilder:
    """Hand back a way to stand up a differently shaped fleet inside a test.

    The `fake_fleet` fixture takes its size from the command line, which is right for a
    measurement of one shape. A test that walks a scaling curve needs to choose the shape
    itself, and must build it out of the same pieces so the two cannot diverge.
    """

    @contextmanager
    def build(remote_count: int, shape: EstateShape) -> Iterator[QueryLog]:
        log = QueryLog()
        sites = build_sites(
            central_site_id=CENTRAL_SITE_ID,
            remote_count=remote_count,
            shape=shape,
            version=fake_version,
            log=log,
            latency=remote_latency,
        )
        with (
            set_config(sites=site_configurations([SiteId(site_id) for site_id in sites])),
            patched_remotes(sites),
        ):
            yield log

    return build
