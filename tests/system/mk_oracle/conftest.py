#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterator
from pathlib import Path
from random import randint

import docker
import docker.client
import pytest

from tests.system.mk_oracle.oracle_database import OracleDatabase


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--mk-oracle-binary-path",
        required=True,
        help="Path to a pre-built mk-oracle binary.",
    )


@pytest.fixture(name="mk_oracle_binary_path", scope="session")
def _mk_oracle_binary_path(request: pytest.FixtureRequest) -> Path:
    value: str = request.config.getoption("--mk-oracle-binary-path")
    return Path(value)


@pytest.fixture(name="client", scope="session")
def _docker_client() -> docker.DockerClient:
    return docker.DockerClient()


@pytest.fixture(name="tmp_path_session", scope="session")
def _tmp_path_session(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("mk_oracle_system_tests")


@pytest.fixture(name="oracle", scope="session")
def _oracle(
    client: docker.client.DockerClient,
    tmp_path_session: Path,
    mk_oracle_binary_path: Path,
) -> Iterator[OracleDatabase]:
    with OracleDatabase(
        client,
        name=f"oracle_{randint(10000000, 99999999)}",
        temp_dir=tmp_path_session,
        mk_oracle_binary_path=mk_oracle_binary_path,
    ) as oracle_db:
        yield oracle_db
