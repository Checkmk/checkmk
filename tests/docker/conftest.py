#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import logging
from collections.abc import Iterator
from random import randint

import pytest

import docker
from tests.testlib.common.version import version_from_env
from tests.testlib.pytest_helpers import diagnostics, registration
from tests.testlib.system.docker import CheckmkApp

logger = logging.getLogger()


def pytest_addoption(parser: pytest.Parser, pluginmanager: pytest.PytestPluginManager) -> None:  # noqa: ARG001
    registration.register_pytest_plugins(pluginmanager, diagnostics)


@pytest.fixture(name="client", scope="session")
def _docker_client() -> docker.DockerClient:
    return docker.DockerClient()


@pytest.fixture(name="checkmk", scope="session")
def _checkmk(client: docker.DockerClient) -> Iterator[CheckmkApp]:
    container_name = f"checkmk-{version_from_env().branch}_{randint(10000000, 99999999)}"
    with CheckmkApp(client, name=container_name, ports={"8000/tcp": None}) as checkmk:
        yield checkmk
