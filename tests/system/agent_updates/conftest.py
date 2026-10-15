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
from pathlib import Path

import pytest

from tests.testlib.common.utils2 import is_containerized
from tests.testlib.system.agent import bake_agents, download_agent_package, get_package_type
from tests.testlib.system.host_under_test import HostUnderTest, LocalHost
from tests.testlib.system.site import get_site_factory, Site, tracing_config_from_env

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
