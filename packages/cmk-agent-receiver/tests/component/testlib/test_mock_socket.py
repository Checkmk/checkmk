#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import secrets
import socket
import time
from pathlib import Path

import pytest

from cmk.testlib.agent_receiver.mock_socket import create_socket

SOCKET_TIMEOUT = 2.0


def test_single_message(socket_path: str) -> None:
    """
    We should be able to send a message.
    Verify that the socket has read the message.
    """
    with create_socket(socket_path=socket_path, socket_timeout=SOCKET_TIMEOUT) as ms:
        _connect_and_send(ms.socket_path, b"message1")
        assert ms.data_queue.get(timeout=SOCKET_TIMEOUT + 2).data == b"message1"
        assert ms.data_queue.empty()


def test_multiple_messages(socket_path: str) -> None:
    """
    We should be able to use the socket for a longer period of time and send messages to it
    from various clients (sequentially). The messages are available before the socket is closed.
    """
    with create_socket(socket_path=socket_path, socket_timeout=SOCKET_TIMEOUT) as ms:
        _connect_and_send(ms.socket_path, b"message1")
        chunk_1 = ms.data_queue.get(timeout=SOCKET_TIMEOUT + 1)
        assert chunk_1.data == b"message1"
        _connect_and_send(ms.socket_path, b"message2")
        chunk_2 = ms.data_queue.get(timeout=SOCKET_TIMEOUT + 1)
        assert chunk_2.data == b"message2"

    assert chunk_1.socket_id != chunk_2.socket_id
    assert ms.data_queue.empty()


def _connect_and_send(socket_path: str, data: bytes) -> None:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.connect(socket_path)
        client.sendall(data)
        client.shutdown(socket.SHUT_RDWR)


def test_socket_timeout(socket_path: str) -> None:
    """
    The socket must be stoppable even if no client connects to it. `Accept` must not block
    indefinitely.
    """
    socket_timeout = 0.5
    with create_socket(socket_path=socket_path, socket_timeout=socket_timeout) as ms:
        time.sleep(socket_timeout + 0.5)

    assert not ms.is_running


@pytest.fixture
def socket_path(tmpdir: Path) -> str:
    return f"{tmpdir}/{secrets.token_urlsafe(8)}-test.sock"
