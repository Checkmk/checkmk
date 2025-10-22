#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket

from cmk.testlib.agent_receiver.mock_socket import create_socket

TIMEOUT = 5.0


def test_single_message() -> None:
    """
    We should be able to send a message.
    Verify that the socket has read the message, at latest after the socket has been closed.
    """
    with create_socket() as ms:
        _connect_and_send(ms.socket_path, b"message1")
    assert ms.data_queue.get() == b"message1"
    assert ms.data_queue.qsize() == 0


def test_multiple_messages() -> None:
    """
    We should be able to use the socket for a longer period of time and send messages to it
    from various clients (sequentially). The messages are available before the socket is closed.
    """
    with create_socket() as ms:
        _connect_and_send(ms.socket_path, b"message1")
        assert ms.data_queue.get(timeout=TIMEOUT) == b"message1"
        _connect_and_send(ms.socket_path, b"message2")
        assert ms.data_queue.get(timeout=TIMEOUT) == b"message2"
    assert ms.data_queue.qsize() == 0


def _connect_and_send(socket_path: str, data: bytes) -> None:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.connect(socket_path)
        client.sendall(data)
