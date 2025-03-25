#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import os
from collections.abc import Iterator
from contextlib import nullcontext
from pathlib import Path

import docker  # type: ignore[import-untyped]
import docker.models  # type: ignore[import-untyped]
import docker.models.containers  # type: ignore[import-untyped]
import docker.models.images  # type: ignore[import-untyped]
import pytest

from tests.testlib.docker import CheckmkApp

logger = logging.getLogger()


@pytest.fixture(name="client", scope="session")
def _docker_client() -> docker.DockerClient:
    return docker.DockerClient()


@pytest.fixture(name="checkmk", scope="session")
def _checkmk(client: docker.DockerClient) -> Iterator[CheckmkApp | None]:
    with (
        CheckmkApp(client, name="checkmk", ports={"8000/tcp": 9000})
        if os.getenv("AGENT_PLUGIN_E2E", "0") == "1"
        else nullcontext()
    ) as checkmk:
        yield checkmk


@pytest.fixture(name="tmp_path_session", scope="session")
def _tmp_path_session(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("agent_plugin_integration")
