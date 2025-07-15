#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
import threading
from collections.abc import Iterator
from pathlib import Path
from shutil import which
from typing import Literal

import pytest

from tests.performance.sysmon import track_resources
from tests.testlib.site import (
    connection,
    get_site_factory,
    GlobalSettingsUpdate,
    Site,
    tracing_config_from_env,
)
from tests.testlib.utils import is_containerized, run

site_factory = get_site_factory(prefix="perf_")

logger = logging.getLogger(__name__)


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--rounds",
        action="store",
        type=int,
        help="The number of rounds used for each scenario.",
        default=5,
    )
    parser.addoption(
        "--warmup-rounds",
        action="store",
        type=int,
        help="The number of warmup rounds used for each scenario.",
        default=0,
    )
    parser.addoption(
        "--iterations",
        action="store",
        type=int,
        help="The number of iterations used for each scenario.",
        default=1,
    )
    parser.addoption(
        "--object-count",
        action="store",
        type=int,
        help="The number of objects created for each scenario.",
        default=1000,
    )


@pytest.fixture(name="track_resources", scope="function")
def _track_resources(request: pytest.FixtureRequest) -> Iterator[None]:
    """Track the resource usage of an entire test case."""
    with track_resources(request.node.name):
        yield


@pytest.fixture(name="central_site", scope="session")
def _central_site(request: pytest.FixtureRequest, ensure_cron: None) -> Iterator[Site]:
    """Provide a default, central monitoring site."""
    setup_stop_event = threading.Event()
    cleanup_start_event = threading.Event()
    with (
        track_resources("setup_central_site", stop_event=setup_stop_event),
        site_factory.get_test_site_ctx(
            "central",
            description=request.node.name,
            auto_restart_httpd=True,
            tracing_config=tracing_config_from_env(os.environ),
            global_settings_updates=[
                GlobalSettingsUpdate(
                    relative_path=Path("etc") / "check_mk" / "multisite.d" / "wato" / "global.mk",
                    update={
                        "log_levels": {
                            "cmk.web": 10,
                            "cmk.web.agent_registration": 10,
                            "cmk.web.background-job": 10,
                        }
                    },
                ),
                GlobalSettingsUpdate(
                    relative_path=Path("etc") / "check_mk" / "conf.d" / "wato" / "global.mk",
                    update={"agent_bakery_logging": 10},
                ),
            ],
        ) as central_site,
        track_resources("teardown_central_site", start_event=cleanup_start_event),
    ):
        setup_stop_event.set()
        with track_resources("stop_central_site"):
            central_site.stop()
        with track_resources("start_central_site"):
            central_site.start()

        # DCD setup
        central_site.write_file(
            "etc/check_mk/dcd.d/wato/global.mk",
            "dcd_activate_changes_timeout = 3600\n"
            "dcd_bulk_discovery_timeout = 3600\n"
            "dcd_site_update_interval = 3600\n",
        )
        central_site.openapi.changes.activate_and_wait_for_completion()
        yield central_site
        cleanup_start_event.set()


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
    central_site: Site, request: pytest.FixtureRequest, ensure_cron: None
) -> Iterator[Site]:
    """Provide a default, remote monitoring site."""
    yield from _make_connected_remote_site("remote", central_site, request.node.name)


@pytest.fixture(name="remote_site_2", scope="session")
def _remote_site_2(
    central_site: Site, request: pytest.FixtureRequest, ensure_cron: None
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
