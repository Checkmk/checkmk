#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
from collections.abc import Iterator
from pathlib import Path

import docker  # type: ignore[import-untyped]
import docker.models  # type: ignore[import-untyped]
import docker.models.containers  # type: ignore[import-untyped]
import docker.models.images  # type: ignore[import-untyped]
import pytest

from tests.testlib.docker import start_checkmk
from tests.testlib.version import CMKVersion, version_from_env

logger = logging.getLogger()


@pytest.fixture(name="version", scope="session")
def _version() -> CMKVersion:
    return version_from_env()


@pytest.fixture(name="client", scope="session")
def _docker_client() -> docker.DockerClient:
    return docker.DockerClient()


@pytest.fixture(name="checkmk", scope="session")
def _checkmk(client: docker.DockerClient) -> Iterator[docker.models.containers.Container]:
    with start_checkmk(client, name="checkmk", ports={"8000/tcp": 9000}) as container:
        yield container


@pytest.fixture(name="tmp_path_session", scope="session")
def _tmp_path_session(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("docker_tests")
