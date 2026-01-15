#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import os
import pathlib
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from cmk.agent_receiver.lib.auth import internal_credentials
from cmk.agent_receiver.lib.config import Config, CONFIG_FILE
from cmk.agent_receiver.main import main_app
from cmk.agent_receiver.relay.api.routers.relays.dependencies import (
    get_forward_monitoring_data_handler,
)
from cmk.agent_receiver.relay.api.routers.relays.handlers import ForwardMonitoringDataHandler
from cmk.testlib.agent_receiver.agent_receiver import AgentReceiverClient
from cmk.testlib.agent_receiver.certs import generate_site_certificate, set_up_ca_certs
from cmk.testlib.agent_receiver.container import Container, run_container
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
) -> Config:
    site_dir = tmp_path / site_name
    site_dir.mkdir(parents=True, exist_ok=True)

    os.environ["OMD_ROOT"] = str(site_dir)
    os.environ["OMD_SITE"] = site_name

    site_conf = site_dir / "etc/omd/site.conf"
    site_conf.parent.mkdir(parents=True, exist_ok=True)
    site_conf.write_text(
        f"CONFIG_APACHE_TCP_ADDR='{wiremock.wiremock_hostname}'\nCONFIG_APACHE_TCP_PORT='{wiremock.port}'\n"
    )

    site_context = Config()
    site_context.internal_secret_path.parent.mkdir(parents=True, exist_ok=True)
    site_context.internal_secret_path.write_text("lol")

    site_context.log_path.parent.mkdir(parents=True, exist_ok=True)
    site_context.log_path.touch()

    (site_context.omd_root / CONFIG_FILE).write_text(site_context.model_dump_json())

    set_up_ca_certs(config=site_context)
    generate_site_certificate(config=site_context)

    # Create version symlink structure
    version_name = "some.detailed.version.ultimate"
    version_path = site_context.omd_root / version_name
    version_path.mkdir(exist_ok=True)
    version_link = site_context.omd_root / "version"
    version_link.symlink_to(version_path)

    return site_context


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

    print(site_context.log_path.read_text())  # nosemgrep: disallow-print


@pytest.fixture(scope="session")
def wiremock_container() -> Iterator[Container]:
    with run_container() as container:
        yield container


@pytest.fixture(scope="session")
def wiremock(wiremock_container: Container) -> Wiremock:
    """
    Provide a Wiremock instance for the tests.
    """
    return Wiremock(
        port=wiremock_container.port,
        wiremock_hostname=wiremock_container.address,
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
