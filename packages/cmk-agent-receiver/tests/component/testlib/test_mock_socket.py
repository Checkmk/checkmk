#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import secrets
import socket
import time
from pathlib import Path

import pytest

from cmk.testlib.agent_receiver.mock_socket import create_socket, MockSocket

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


def test_socket_is_closed_by_context_manager(socket_path: str) -> None:
    socket_timeout = 0.5
    saved_socket: MockSocket
    with create_socket(socket_path=socket_path, socket_timeout=socket_timeout) as ms:
        saved_socket = ms
    assert saved_socket.fileno == -1, "Socket was not closed"


def test_socket_busy_queuing(socket_path: str) -> None:
    """
    Test that the mock socket handles OS-level connection queuing correctly.

    When one client is connected and actively using the socket, a second client's
    connection attempt should be queued by the OS. Once the first client finishes,
    the second client should be able to send its data successfully.

    This verifies the mock socket implementation behaves like a real UNIX domain socket
    with respect to the OS kernel's accept queue.
    """
    import threading

    first_payload = b"first-client-data"
    second_payload = b"second-client-data"

    # Barrier to synchronize the two clients
    connection_barrier = threading.Barrier(2, timeout=10)

    def slow_client() -> None:
        """First client that connects and delays before sending."""
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.connect(socket_path)
            # Signal that we're connected
            connection_barrier.wait()
            # Delay to keep the socket busy
            time.sleep(0.5)
            sock.sendall(first_payload)
            sock.shutdown(socket.SHUT_RDWR)

    with create_socket(socket_path=socket_path, socket_timeout=SOCKET_TIMEOUT * 2) as ms:
        # Start the slow client
        slow_thread = threading.Thread(target=slow_client)
        slow_thread.start()

        # Wait for slow client to connect
        connection_barrier.wait()

        # Now start the second client while the first is still connected
        _connect_and_send(socket_path, second_payload)
        slow_thread.join()

        # Both payloads should be received, in order
        chunk_1 = ms.data_queue.get(timeout=SOCKET_TIMEOUT + 2)
        chunk_2 = ms.data_queue.get(timeout=SOCKET_TIMEOUT + 2)

        assert chunk_1.data == first_payload
        assert chunk_2.data == second_payload
        # Different connections should have different socket IDs
        assert chunk_1.socket_id != chunk_2.socket_id
        assert ms.data_queue.empty()


@pytest.fixture
def socket_path(tmpdir: Path) -> str:
    return f"{tmpdir}/{secrets.token_urlsafe(8)}-test.sock"
