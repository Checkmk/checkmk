#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pathlib
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from cmk.agent_receiver.lib.auth import internal_credentials
from cmk.agent_receiver.lib.config import Config, get_config
from cmk.agent_receiver.main import main_app
from cmk.agent_receiver.relay.api.routers.relays.dependencies import (
    get_forward_monitoring_data_handler,
)
from cmk.agent_receiver.relay.api.routers.relays.handlers import ForwardMonitoringDataHandler
from cmk.testlib.agent_receiver.agent_receiver import AgentReceiverClient
from cmk.testlib.agent_receiver.builder import AgentReceiverConfigBuilder
from cmk.testlib.agent_receiver.native_wiremock import run_wiremock
from cmk.testlib.agent_receiver.site_mock import SiteMock, User
from cmk.testlib.agent_receiver.wiremock import Wiremock


@pytest.fixture()
def site_name() -> str:
    return "my_component_test_site"


@pytest.fixture()
def site_context(
    wiremock: Wiremock,
    tmp_path: pathlib.Path,
    site_name: str,
    monkeypatch: pytest.MonkeyPatch,
) -> Config:
    built = AgentReceiverConfigBuilder(
        omd_root=tmp_path / site_name,
        site_name=site_name,
        apache_address=wiremock.wiremock_hostname,
        apache_port=wiremock.port,
    ).build()
    for key, value in built.env.items():
        monkeypatch.setenv(key, value)
    get_config.cache_clear()
    return built.config


@pytest.fixture()
def test_client(site_context: Config) -> Iterator[TestClient]:
    """Test client for agent receiver.

    Use this with AgentReceiverClient.with_client_ip() context manager
    for endpoints that require localhost access.
    """
    app = main_app()

    # Override the ForwardMonitoringDataHandler to use a shorter timeout for tests
    def get_test_forward_monitoring_data_handler(config: Config) -> ForwardMonitoringDataHandler:
        return ForwardMonitoringDataHandler(data_socket=config.raw_data_socket, socket_timeout=2.0)

    app.dependency_overrides[get_forward_monitoring_data_handler] = (
        get_test_forward_monitoring_data_handler
    )

    client = TestClient(app)
    yield client

    print(site_context.log_path.read_text())


@pytest.fixture(scope="session")
def wiremock() -> Iterator[Wiremock]:
    """
    Provide a Wiremock instance for the tests.
    """
    with run_wiremock() as process:
        yield Wiremock(
            port=process.http_port,
            wiremock_hostname=process.hostname,
        )


@pytest.fixture
def user() -> User:
    return User("testmo", "supersecret")


@pytest.fixture
def site(wiremock: Wiremock, user: User, site_context: Config) -> SiteMock:
    """
    Create a site mock instance.
    """
    wiremock.reset()
    return SiteMock(wiremock, site_context.site_name, user, internal_credentials())


@pytest.fixture
def agent_receiver(
    test_client: TestClient, site_context: Config, user: User
) -> AgentReceiverClient:
    """Agent receiver client with dynamic IP control.

    Use with_client_ip() context manager for localhost-only operations:
        with agent_receiver.with_client_ip("127.0.0.1"):
            agent_receiver.push_task(...)

    Use directly for relay operations:
        agent_receiver.get_relay_tasks(...)
    """
    return AgentReceiverClient(test_client, site_context.site_name, user)
