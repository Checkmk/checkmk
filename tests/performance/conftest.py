#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# ruff: noqa: ARG001  # Unused fixtures are needed for setup side effects

import logging
import os
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from shutil import which
from typing import Literal

import pytest

# Has to precede the imports below: a module already imported cannot be rewritten, and it is
# the scenarios that carry the assertions now - `perftest` holds only the state they share.
pytest.register_assert_rewrite(
    "tests.performance.activation.scenario",
    "tests.performance.dcd.scenario",
    "tests.performance.hosts.scenario",
    "tests.performance.nagios.scenario",
    "tests.performance.services.scenario",
    "tests.performance.ui_response.scenario",
)

from tests.performance.perftest import PerformanceTest  # noqa: E402
from tests.performance.sysmon import track_resources  # noqa: E402
from tests.testlib.common.utils2 import is_containerized, run  # noqa: E402
from tests.testlib.site import (  # noqa: E402
    connection,
    get_site_factory,
    GlobalSettingsUpdate,
    Site,
    tracing_config_from_env,
)

site_factory = get_site_factory(prefix="perf_")

# The in-process half of the monitoring-view comparison is a Bazel suite: it runs the GUI in this
# process against faked `cmk.utils.paths`, which its conftest sets up at import time. Collecting it
# inside a run that drives real sites would repoint those paths at a temp directory and break every
# site test, so it is reached only through its own Bazel target. Its own directory is what gets
# named here, because a conftest is loaded whenever the directory holding it is collected at all.
collect_ignore = ["monitoring_views/in_process"]

logger = logging.getLogger(__name__)


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--iterations",
        action="store",
        type=int,
        help=(
            "The number of iterations used for each scenario call. "
            "Iterations may be grouped into rounds. "
            "Must be 1 for scenarios with setup and teardown logic."
        ),
        default=1,
    )
    parser.addoption(
        "--rounds",
        action="store",
        type=int,
        help=(
            "The number of rounds (i.e. batches) of iterations used for each scenario. "
            "Any setup and teardown logic will per executed once per round."
        ),
        default=16,
    )
    parser.addoption(
        "--warmup-rounds",
        action="store",
        type=int,
        help="The number of warmup rounds used for each scenario.",
        default=0,
    )
    parser.addoption(
        "--fake-remotes",
        action="store",
        type=int,
        help=(
            "Number of faked Livestatus remote sites to serve and connect to the central site, "
            "for the monitoring-view comparison. Zero uses the real distributed setup instead. "
            "Faked by default: a faked remote costs the central site what a real one does (see "
            "the fidelity test in the same module), and twenty of them fit on one machine."
        ),
        default=20,
    )
    parser.addoption(
        "--fake-remote-hosts",
        action="store",
        type=int,
        help="Number of hosts each faked remote site monitors.",
        default=500,
    )
    parser.addoption(
        "--fake-remote-latency-ms",
        action="store",
        type=float,
        help=(
            "Delay every faked remote adds before answering, in milliseconds. A fan-out is "
            "issued in parallel, so this costs one link's latency per round trip a page takes - "
            "which is what makes the round-trip difference between two pages visible."
        ),
        default=0.0,
    )
    parser.addoption(
        "--fake-remote-proxy",
        action="store_true",
        help=(
            "Reach the faked remotes through the Livestatus proxy, the way the commercial "
            "editions reach a distributed setup, instead of connecting to each site directly."
        ),
        default=False,
    )
    parser.addoption(
        "--row-limit-real",
        action="store",
        choices=("soft", "hard", "none"),
        help=(
            "Which row limit the monitoring pages are measured at against a real site: 'soft' "
            "(1000 rows, either page's default), 'hard' (5000) or 'none' (no limit)."
        ),
        default="soft",
    )
    parser.addoption(
        "--object-count",
        action="store",
        type=int,
        help="The number of objects created for each scenario.",
        default=100,
    )
    parser.addoption(
        "--mocked-sites",
        action="store",
        type=int,
        help="The number of mocked remote sites used for the mocked distributed scenarios.",
        default=30,
    )
    parser.addoption(
        "--pb-hosts",
        action="store",
        type=int,
        help=(
            "The total number of piggybacked hosts for the distributed piggyback "
            "scenarios (default: 2 * object-count)."
        ),
        default=None,
    )


@pytest.fixture(name="track_system_resources", scope="function")
def _track_resources(request: pytest.FixtureRequest) -> Iterator[None]:
    """Track the resource usage of the entire system during the test case execution."""
    with track_resources(request.node.name):
        yield


@contextmanager
def _site(description: str, distributed: bool) -> Iterator[Site]:
    """Provide a default monitoring site."""
    site_name = "central" if distributed else "single"
    setup_stop_event = threading.Event()
    cleanup_start_event = threading.Event()
    global_settings_updates = [
        GlobalSettingsUpdate(
            relative_path=Path("etc") / "check_mk" / "multisite.d" / "wato" / "global.mk",
            update={
                "log_levels": {
                    "cmk.web": 10,
                    "cmk.web.agent_registration": 10,
                    "cmk.web.background-job": 10,
                }
            },
        )
    ]
    if distributed:
        global_settings_updates.append(
            GlobalSettingsUpdate(
                relative_path=Path("etc") / "check_mk" / "conf.d" / "wato" / "global.mk",
                update={"agent_bakery_logging": 10},
            )
        )
    with (
        track_resources(f"setup_{site_name}_site", stop_event=setup_stop_event),
        site_factory.get_test_site_ctx(
            site_name,
            description=description,
            auto_restart_httpd=True,
            tracing_config=tracing_config_from_env(os.environ),
            global_settings_updates=global_settings_updates,
        ) as site,
        track_resources(f"teardown_{site_name}_site", start_event=cleanup_start_event),
    ):
        setup_stop_event.set()
        with track_resources(f"stop_{site_name}_site"):
            site.stop()
        with track_resources(f"start_{site_name}_site"):
            site.start()

        # DCD setup
        site.write_file(
            "etc/check_mk/dcd.d/wato/global.mk",
            "dcd_activate_changes_timeout = 3600\n"
            "dcd_bulk_discovery_timeout = 3600\n"
            "dcd_site_update_interval = 3600\n",
        )
        site.openapi.changes.activate_and_wait_for_completion()
        yield site
        cleanup_start_event.set()


@pytest.fixture(name="single_site", scope="session")
def _single_site(request: pytest.FixtureRequest, ensure_cron: None) -> Iterator[Site]:
    """Provide a default, single monitoring site."""
    with _site(description=request.node.name, distributed=False) as single_site:
        hosts = {
            "local": {
                "ipaddress": "127.0.0.1",
                "tag_address_family": "ip-v4-only",
            },
            "dummy": {
                "tag_address_family": "no-ip",
                "tag_agent": "no-agent",
                "tag_snmp_ds": "no-snmp",
            },
        }
        activate_changes = False
        for host_name, attributes in hosts.items():
            if not single_site.openapi.hosts.get(host_name):
                single_site.openapi.hosts.create(
                    host_name,
                    "/",
                    attributes=attributes,
                )
                activate_changes = True
        if activate_changes:
            single_site.openapi.changes.activate_and_wait_for_completion()
        yield single_site


@pytest.fixture(name="central_site", scope="session")
def _central_site(request: pytest.FixtureRequest, ensure_cron: None) -> Iterator[Site]:
    """Provide a default, central monitoring site."""
    with _site(description=request.node.name, distributed=True) as central_site:
        yield central_site


def _make_connected_remote_site(
    site_name: Literal["remote", "remote2"],  # just to track what we're doing...
    central_site: Site,
    site_description: str,
) -> Iterator[Site]:
    """Connect a given remote site to a central site.

    Args:
        site_name: The name of the remote_site to connect.
        central_site: The central site to connect to.
        site_description: A description to be used for the connection.
    """
    with (
        site_factory.get_test_site_ctx(
            site_name,
            description=site_description,
            auto_restart_httpd=True,
            tracing_config=tracing_config_from_env(os.environ),
        ) as remote_site,
        connection(central_site=central_site, remote_site=remote_site),
    ):
        yield remote_site


@pytest.fixture(name="remote_site", scope="session")
def _remote_site(
    central_site: Site,
    request: pytest.FixtureRequest,
    ensure_cron: None,
) -> Iterator[Site]:
    """Provide a default, remote monitoring site."""
    yield from _make_connected_remote_site("remote", central_site, request.node.name)


@pytest.fixture(name="remote_site_2", scope="session")
def _remote_site_2(
    central_site: Site,
    request: pytest.FixtureRequest,
    ensure_cron: None,
) -> Iterator[Site]:
    """Provide a second default, central monitoring site."""
    yield from _make_connected_remote_site("remote2", central_site, request.node.name)


@pytest.fixture(scope="session", name="ensure_cron")
def _run_cron() -> None:
    """Run cron for background jobs"""
    if not is_containerized():
        return

    logger.info("Ensure system cron is running")

    # cron  - Ubuntu, Debian, ...
    # crond - RHEL (AlmaLinux)
    cron_cmd = "crond" if Path("/etc/redhat-release").exists() else "cron"

    if not which(cron_cmd):
        raise RuntimeError(f"No cron executable found (tried {cron_cmd})")

    if run(["pgrep", cron_cmd], check=False, capture_output=True).returncode == 0:
        return

    # Start cron daemon. It forks an will keep running in the background
    run([cron_cmd], check=True, sudo=True)


@pytest.fixture(scope="session")
def browser_context_args() -> dict[str, dict[str, str]]:
    """Configure the browser context in pytest-playwright.

    Set headers to disable caching.
    """
    return {
        "extra_http_headers": {
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Connection": "close",
        }
    }


@pytest.fixture(name="perftest", scope="module")
def _perftest(single_site: Site, pytestconfig: pytest.Config) -> PerformanceTest:
    """The shared state of a scenario measured against one site."""
    return PerformanceTest(single_site, remote_sites=None, pytestconfig=pytestconfig)


@pytest.fixture(name="perftest_dist", scope="module")
def _perftest_dist(
    central_site: Site,
    remote_site: Site,
    remote_site_2: Site,
    pytestconfig: pytest.Config,
) -> PerformanceTest:
    """The same, for a scenario that needs a central site with remotes attached."""
    return PerformanceTest(
        central_site, remote_sites=[remote_site, remote_site_2], pytestconfig=pytestconfig
    )


def pytest_terminal_summary(terminalreporter: pytest.TerminalReporter) -> None:
    """Print the monitoring-page comparison, if this run produced one."""
    from tests.performance.monitoring_views.test_monitoring_views import REPORT

    if not (lines := REPORT.lines()):
        return
    terminalreporter.write_sep("=", "monitoring page comparison (real site)")
    for line in lines:
        terminalreporter.write_line(line)
