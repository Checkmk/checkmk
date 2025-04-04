#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
from collections.abc import Iterator
from random import randint

import docker  # type: ignore[import-untyped]
import docker.models  # type: ignore[import-untyped]
import docker.models.containers  # type: ignore[import-untyped]
import docker.models.images  # type: ignore[import-untyped]
import pytest

from tests.testlib.docker import CheckmkApp
from tests.testlib.version import version_from_env

logger = logging.getLogger()


@pytest.fixture(name="client", scope="session")
def _docker_client() -> docker.DockerClient:
    return docker.DockerClient()


@pytest.fixture(name="checkmk", scope="session")
def _checkmk(client: docker.DockerClient) -> Iterator[CheckmkApp]:
    container_name = f"checkmk-{version_from_env().branch}_{randint(10000000, 99999999)}"
    with CheckmkApp(client, name=container_name, ports={"8000/tcp": 9000}) as checkmk:
        yield checkmk
