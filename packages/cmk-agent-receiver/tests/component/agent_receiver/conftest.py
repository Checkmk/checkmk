#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pathlib
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from cmk.agent_receiver.lib.config import get_config
from cmk.agent_receiver.main import main_app
from cmk.testlib.agent_receiver.builder import AgentReceiverConfigBuilder, AgentReceiverSite
from cmk.testlib.agent_receiver.native_wiremock import run_wiremock
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
        omd_root=tmp_path / "some-test-name",
        site_name="some-test-name",
        apache_address=wiremock.wiremock_hostname,
        apache_port=wiremock.port,
    ).build()


@pytest.fixture()
def test_client(
    ar_site: AgentReceiverSite, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    for key, value in ar_site.env.items():
        monkeypatch.setenv(key, value)
    get_config.cache_clear()
    yield TestClient(main_app())

    print(ar_site.config.log_path.read_text())  # noqa: T201  # It's OK for test/script helpers to print()
