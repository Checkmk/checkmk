#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pathlib
from collections.abc import Iterator

import pytest

from cmk.testlib.agent_receiver.builder import AgentReceiverConfigBuilder, AgentReceiverSite
from cmk.testlib.agent_receiver.native_wiremock import run_wiremock
from cmk.testlib.agent_receiver.runner import AgentReceiverRunner
from cmk.testlib.agent_receiver.wiremock import Wiremock


@pytest.fixture(scope="session")
def wiremock() -> Iterator[Wiremock]:
    with run_wiremock() as process:
        yield Wiremock(
            port=process.http_port,
            wiremock_hostname=process.hostname,
        )


@pytest.fixture()
def ar_site(wiremock: Wiremock, tmp_path: pathlib.Path) -> AgentReceiverSite:
    wiremock.reset()
    return AgentReceiverConfigBuilder(
        omd_root=tmp_path / "site",
        site_name="site",
        apache_address=wiremock.wiremock_hostname,
        apache_port=wiremock.port,
    ).build()


@pytest.fixture
def ar_runner(ar_site: AgentReceiverSite) -> Iterator[AgentReceiverRunner]:
    runner = AgentReceiverRunner(ar_site)
    with runner.running():
        runner.wait_for_running()
        yield runner
