#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
from collections.abc import Iterator
from pathlib import Path
from shutil import which
from typing import Literal

import pytest
from opentelemetry.instrumentation.requests import RequestsInstrumentor

from tests.composition.utils import get_cre_agent_path

from tests.testlib.agent import (
    agent_controller_daemon,
    bake_agents,
    download_and_install_agent_package,
    install_agent_package,
)
from tests.testlib.site import (
    connection,
    get_site_factory,
    GlobalSettingsUpdate,
    Site,
    tracing_config_from_env,
)
from tests.testlib.utils import is_containerized, run

site_factory = get_site_factory(prefix="comp_")

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session", autouse=True)
def instrument_requests() -> None:
    RequestsInstrumentor().instrument()


@pytest.fixture(name="central_site", scope="session")
def _central_site(request: pytest.FixtureRequest, ensure_cron: None) -> Iterator[Site]:
    with site_factory.get_test_site_ctx(
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
    ) as central_site:
        yield central_site


@pytest.fixture(name="remote_site", scope="session")
def _remote_site(
    central_site: Site, request: pytest.FixtureRequest, ensure_cron: None
) -> Iterator[Site]:
    yield from _make_connected_remote_site("remote", central_site, request.node.name)


@pytest.fixture(name="remote_site_2", scope="session")
def _remote_site_2(
    central_site: Site, request: pytest.FixtureRequest, ensure_cron: None
) -> Iterator[Site]:
    yield from _make_connected_remote_site("remote2", central_site, request.node.name)


def _make_connected_remote_site(
    site_name: Literal["remote", "remote2"],  # just to track what we're doing...
    central_site: Site,
    site_description: str,
) -> Iterator[Site]:
    with site_factory.get_test_site_ctx(
        site_name,
        description=site_description,
        auto_restart_httpd=True,
        tracing_config=tracing_config_from_env(os.environ),
    ) as remote_site:
        with connection(central_site=central_site, remote_site=remote_site):
            yield remote_site


@pytest.fixture(name="installed_agent_ctl_in_unknown_state", scope="function")
def _installed_agent_ctl_in_unknown_state(central_site: Site, tmp_path: Path) -> Path:
    if central_site.edition.is_raw_edition():
        return install_agent_package(get_cre_agent_path(central_site))
    bake_agents(central_site)
    return download_and_install_agent_package(central_site, tmp_path)


@pytest.fixture(name="agent_ctl", scope="function")
def _agent_ctl(installed_agent_ctl_in_unknown_state: Path) -> Iterator[Path]:
    with agent_controller_daemon(installed_agent_ctl_in_unknown_state):
        yield installed_agent_ctl_in_unknown_state


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
