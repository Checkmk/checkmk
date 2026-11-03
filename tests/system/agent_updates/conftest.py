#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Fixtures for the agent update system tests.

The cases install the Checkmk agent on the host under test and change its registrations. On a
developer machine that host is the machine itself, so run them with
`tests/run_tests.sh test-system-agent-updates-docker`.
"""

import os
from collections.abc import Iterator
from pathlib import Path, PurePosixPath

import pytest

from tests.testlib.common.utils2 import is_containerized
from tests.testlib.system.agent import (
    AGENT_CTL,
    bake_agents,
    download_agent_package,
    get_package_type,
    install_agent_package,
    purge_agent_package,
)
from tests.testlib.system.host_under_test import HostUnderTest, LocalHost
from tests.testlib.system.site import get_site_factory, Site, tracing_config_from_env
from tests.testlib.system.systemd import require_systemd, systemd_managed_agent_controller

_ALLOW_LOCAL_HOST = "CMK_ALLOW_AGENT_ON_LOCAL_HOST"


@pytest.fixture(name="host", scope="session")
def _host() -> HostUnderTest:
    # Exit rather than skip: a nightly job that lost its container must not turn green.
    if not is_containerized() and os.environ.get(_ALLOW_LOCAL_HOST) != "1":
        pytest.exit(
            "These tests install the Checkmk agent and change its registrations on the machine "
            "they run on. Refusing to do that outside a container. Run 'tests/run_tests.sh "
            f"test-system-agent-updates-docker' instead, or set {_ALLOW_LOCAL_HOST}=1 if you "
            "really mean it.",
            returncode=pytest.ExitCode.USAGE_ERROR,
        )
    return LocalHost()


@pytest.fixture(name="site", scope="session")
def _site(request: pytest.FixtureRequest) -> Iterator[Site]:
    with get_site_factory(prefix="au_").get_test_site_ctx(
        "central",
        description=request.node.name,
        auto_restart_httpd=True,
        tracing_config=tracing_config_from_env(os.environ),
    ) as this_site:
        yield this_site


@pytest.fixture(name="agent_package", scope="session")
def _agent_package(
    host: HostUnderTest, site: Site, tmp_path_factory: pytest.TempPathFactory
) -> Path:
    if not site.edition.is_community_edition():
        bake_agents(site)
    return download_agent_package(
        site, get_package_type(host), tmp_path_factory.mktemp("agent_package")
    )


@pytest.fixture(name="systemd", scope="session")
def _systemd(host: HostUnderTest) -> None:
    # Fail rather than skip, for the same reason the host fixture exits.
    try:
        require_systemd(host)
    except RuntimeError as excp:
        pytest.fail(str(excp))


@pytest.fixture(name="installed_agent_ctl", scope="session")
def _installed_agent_ctl(
    systemd: None,  # noqa: ARG001
    host: HostUnderTest,
    agent_package: Path,
) -> PurePosixPath:
    """The package is installed when the first case needs it.

    Every case that reinstalls or removes the package has to leave it installed again.
    """
    install_agent_package(agent_package, host)
    return AGENT_CTL


@pytest.fixture(name="agent_not_installed")
def _agent_not_installed(host: HostUnderTest) -> None:
    purge_agent_package(host=host)


@pytest.fixture(name="agent_ctl")
def _agent_ctl(host: HostUnderTest, installed_agent_ctl: PurePosixPath) -> Iterator[PurePosixPath]:
    with systemd_managed_agent_controller(host, installed_agent_ctl):
        yield installed_agent_ctl
