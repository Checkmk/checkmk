#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from cmk.base.automation_helper import _server
from cmk.base.automation_helper._config import ServerConfig


@pytest.fixture(name="short_dir")
def fixture_short_dir() -> Iterator[Path]:
    # Unix socket paths are limited to ~108 bytes, which pytest's tmp_path may exceed.
    with tempfile.TemporaryDirectory(dir="/tmp") as directory:
        yield Path(directory)


def _server_config(directory: Path) -> ServerConfig:
    return ServerConfig(
        unix_socket_path=directory / "helper.sock",
        unix_socket_permissions=0o600,
        pid_file=directory / "helper.pid",
        access_log=directory / "access.log",
        error_log=directory / "error.log",
        worker_log=directory / "worker.log",
        num_workers=1,
    )


def test_clients_are_queued_before_the_server_accepts(
    short_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _server_config(short_dir)

    def connect_while_workers_load(*_args: object, **_kwargs: object) -> None:
        # Nobody accepts yet; a refused connection propagates out of run().
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(1)
            client.connect(str(config.unix_socket_path))

    monkeypatch.setattr(_server, "run_uvicorn_server", connect_while_workers_load)

    _server.run(config, "unused:factory")
