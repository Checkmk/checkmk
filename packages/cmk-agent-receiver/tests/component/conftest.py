#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import os
import pathlib
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from cmk.agent_receiver.config import Config, CONFIG_FILE
from cmk.agent_receiver.main import main_app
from cmk.agent_receiver.utils import internal_credentials
from cmk.testlib.agent_receiver.agent_receiver import AgentReceiverClient
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

    site_context = Config(site_url=wiremock.base_url)
    site_context.internal_secret_path.parent.mkdir(parents=True, exist_ok=True)
    site_context.internal_secret_path.write_text("lol")

    site_context.log_path.parent.mkdir(parents=True, exist_ok=True)
    site_context.log_path.touch()

    (site_context.omd_root / CONFIG_FILE).write_text(site_context.model_dump_json())

    return site_context


@pytest.fixture()
def test_client(site_context: Config) -> Iterator[TestClient]:
    # setting up some checkmk stuff required by the agent receiver
    # start the app
    app = main_app()

    client = TestClient(app)
    yield client
    print(site_context.log_path.read_text())


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
    return AgentReceiverClient(test_client, site_context.site_name, user)
