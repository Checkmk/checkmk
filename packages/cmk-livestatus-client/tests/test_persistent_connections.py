#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest

from cmk.livestatus_client import SingleSiteConnection


@pytest.fixture(name="socket_url")
def fixture_socket_url(tmp_path: Path) -> Iterator[str]:
    path = tmp_path / "live"
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
        server.bind(str(path))
        server.listen(5)
        yield f"unix:{path}"


def _connect(socket_url: str) -> SingleSiteConnection:
    connection = SingleSiteConnection(socket_url, persist=True)
    connection.connect()
    return connection


def test_persistent_connection_is_reused_within_a_thread(socket_url: str) -> None:
    first = _connect(socket_url)
    try:
        assert _connect(socket_url).socket is first.socket
    finally:
        first.disconnect()


def test_persistent_connection_is_not_shared_between_threads(socket_url: str) -> None:
    first = _connect(socket_url)
    other_threads_sockets: list[socket.socket | None] = []

    def connect_in_other_thread() -> None:
        connection = _connect(socket_url)
        other_threads_sockets.append(connection.socket)
        connection.disconnect()

    try:
        thread = threading.Thread(target=connect_in_other_thread)
        thread.start()
        thread.join()
        assert other_threads_sockets[0] is not first.socket
    finally:
        first.disconnect()
