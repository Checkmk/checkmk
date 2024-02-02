#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging

import docker  # type: ignore[import-untyped]
import pytest

from tests.testlib.docker import start_checkmk
from tests.testlib.version import CMKVersion, version_from_env

logger = logging.getLogger()


@pytest.fixture(scope="session")
def version() -> CMKVersion:
    return version_from_env()


@pytest.fixture(name="client")
def _docker_client() -> docker.DockerClient:
    return docker.DockerClient()


@pytest.fixture(name="checkmk")
def _checkmk(client: docker.DockerClient) -> docker.models.containers.Container:
    with start_checkmk(client, name="checkmk", ports={"8000/tcp": 9000}) as container:
        yield container
