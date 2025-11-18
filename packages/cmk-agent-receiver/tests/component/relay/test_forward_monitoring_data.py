#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import base64
import queue
import secrets
import socket
import threading
import time
import uuid
from collections.abc import Iterator
from http import HTTPStatus
from pathlib import Path
from unittest.mock import patch

import pytest

from cmk.agent_receiver.lib.config import Config
from cmk.agent_receiver.relay.api.routers.relays.handlers.forward_monitoring_data import (
    SOCKET_TIMEOUT,
)
from cmk.agent_receiver.relay.lib.shared_types import RelayID
from cmk.relay_protocols.monitoring_data import MonitoringData
from cmk.testlib.agent_receiver.agent_receiver import AgentReceiverClient, register_relay
from cmk.testlib.agent_receiver.config_file_system import create_config_folder
from cmk.testlib.agent_receiver.mock_socket import (
    create_non_listening_socket,
    create_socket,
    MockSocket,
)
from cmk.testlib.agent_receiver.site_mock import OP, SiteMock

HOST = "testhost"


def test_forward_monitoring_data(
    socket_path: str,
    relay_id: str,
    serial: str,
    agent_receiver: AgentReceiverClient,
) -> None:
    payload = b"monitoring payload"
    timestamp = int(time.time())
    expected_header = (
        f"payload_type:fetcher;"
        f"payload_size:{len(payload)};"
        f"config_serial:{serial};"
        f"start_timestamp:{timestamp};"
        f"host_by_name:{HOST};"
    )
    saved_socket: MockSocket  # assigned in with-block
    with create_socket(socket_path=socket_path, socket_timeout=SOCKET_TIMEOUT) as ms:
        saved_socket = ms
        monitoring_data = MonitoringData(
            serial=serial,
            host=HOST,
            timestamp=timestamp,
            payload=base64.b64encode(payload),
        )
        response = agent_receiver.forward_monitoring_data(
            relay_id=relay_id,
            monitoring_data=monitoring_data,
        )
        assert response.status_code == HTTPStatus.NO_CONTENT
        chunk = ms.data_queue.get(timeout=SOCKET_TIMEOUT)
        lines = chunk.data.splitlines()
        assert lines[0].decode() == expected_header
        assert lines[1] == payload

    # socket should be closed after context manager exits
    assert saved_socket.fileno == -1, "Socket was not closed"


def test_forward_monitoring_data_with_delay(
    socket_path: str,
    relay_id: str,
    serial: str,
    agent_receiver: AgentReceiverClient,
) -> None:
    """
    If the socket is slower in accepting data, the data can still be forwarded.
    Note: the configured socket timeouts don't seem to have an effect (on UNIX sockets at least).
    """
    delay = SOCKET_TIMEOUT + 1

    with create_socket(socket_path=socket_path, socket_timeout=SOCKET_TIMEOUT, delay=delay) as ms:
        payload = b"monitoring payload"
        monitoring_data = MonitoringData(
            serial=serial,
            host=HOST,
            timestamp=int(time.time()),
            payload=base64.b64encode(payload),
        )
        response = agent_receiver.forward_monitoring_data(
            relay_id=relay_id,
            monitoring_data=monitoring_data,
        )
        assert response.status_code == HTTPStatus.NO_CONTENT, response.text
        chunk = ms.data_queue.get(timeout=SOCKET_TIMEOUT + delay + 1)
        assert_monitoring_data_payload(chunk.data, payload)


def assert_monitoring_data_payload(received_data: bytes, expected_payload: bytes) -> None:
    _, received_payload = received_data.splitlines()
    assert received_payload == expected_payload


def test_socket_busy_but_not_timeout(
    socket_path: str, relay_id: str, serial: str, agent_receiver: AgentReceiverClient
) -> None:
    """
    If a previous client keeps the socket busy, but not long enough to cause a timeout,
    then the handler will wait for that client to finish its business before sending the data.
    """

    slow_client_payload = b"slow-payload"
    regular_payload = b"regular-payload"

    monitoring_data = MonitoringData(
        serial=serial,
        host=HOST,
        timestamp=int(time.time()),
        payload=base64.b64encode(regular_payload),
    )

    sleep = 2.0
    assert SOCKET_TIMEOUT > sleep

    connection_barrier = threading.Barrier(2, timeout=10)
    send_barrier = threading.Barrier(2, timeout=10)
    close_barrier = threading.Barrier(2, timeout=10)

    with create_socket(socket_path=socket_path, socket_timeout=SOCKET_TIMEOUT * 2) as ms:
        slow_client_thread = threading.Thread(
            target=slow_client_thread_func,
            kwargs={
                "socket_path": socket_path,
                "connection_barrier": connection_barrier,
                "send_barrier": send_barrier,
                "close_barrier": close_barrier,
                "payload": slow_client_payload,
            },
        )
        slow_client_thread.start()
        connection_barrier.wait()

        # At this moment the slow client is connected, but has not sent any data yet.

        # Let the slow client sleep for a while, then this agent_receiver client sends data (while the slow client is connected).
        # Don't sleep more than SOCKET_TIMEOUT.

        time.sleep(sleep)
        response = agent_receiver.forward_monitoring_data(
            relay_id=relay_id,
            monitoring_data=monitoring_data,
        )

        # Let the slow client send data.
        send_barrier.wait()

        # Let the slow client close.
        close_barrier.wait()
        slow_client_thread.join()

        assert response.status_code == HTTPStatus.NO_CONTENT, response.text

        chunk_1 = ms.data_queue.get(timeout=SOCKET_TIMEOUT + sleep + 1)
        chunk_2 = ms.data_queue.get(timeout=SOCKET_TIMEOUT + sleep + 1)

    assert chunk_1.data == slow_client_payload
    assert_monitoring_data_payload(chunk_2.data, regular_payload)
    assert chunk_1.socket_id != chunk_2.socket_id
    assert ms.data_queue.empty()


def slow_client_thread_func(
    *,
    socket_path: str,
    connection_barrier: threading.Barrier,
    send_barrier: threading.Barrier,
    close_barrier: threading.Barrier,
    payload: bytes,
) -> None:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.connect(socket_path)
        connection_barrier.wait()

        send_barrier.wait()
        try:
            sock.sendall(payload)
        except BrokenPipeError:
            pass

        close_barrier.wait()
        sock.shutdown(socket.SHUT_RDWR)


def test_socket_busy_slow_send(
    socket_path: str, relay_id: str, serial: str, agent_receiver: AgentReceiverClient
) -> None:
    """
    If a previous client keeps the socket busy, long enough to cause a timeout,
    then the handler should return 502 Bad Gateway.
    The slow client is quick to connect, but slow when sending data.

    Note: cannot make the handler return 502 in this case. Instead, the requests seem to be buffered.
    """

    slow_client_payload = b"slow-payload"
    regular_payload = b"regular-payload"

    monitoring_data = MonitoringData(
        serial=serial,
        host=HOST,
        timestamp=int(time.time()),
        payload=base64.b64encode(regular_payload),
    )

    send_sleep = SOCKET_TIMEOUT + 2

    connection_barrier = threading.Barrier(2, timeout=10)
    send_barrier = threading.Barrier(2, timeout=10)
    close_barrier = threading.Barrier(2, timeout=10)

    with create_socket(socket_path=socket_path, socket_timeout=SOCKET_TIMEOUT) as ms:
        slow_client_thread = threading.Thread(
            target=slow_client_thread_func,
            kwargs={
                "socket_path": socket_path,
                "connection_barrier": connection_barrier,
                "send_barrier": send_barrier,
                "close_barrier": close_barrier,
                "payload": slow_client_payload,
            },
        )
        slow_client_thread.start()
        connection_barrier.wait()

        # At this moment the slow client is connected, but has not sent any data yet.

        # The agent_receiver client sends data, although the slow client is connected.

        response = agent_receiver.forward_monitoring_data(
            relay_id=relay_id,
            monitoring_data=monitoring_data,
        )

        # Do a long sleep (more than SOCKET_TIMEOUT), then let the slow client send data.
        # This request from slow client will be ignored.

        time.sleep(send_sleep)
        send_barrier.wait()

        # Let the slow client close.

        close_barrier.wait()
        slow_client_thread.join()

        assert response.status_code == HTTPStatus.NO_CONTENT, response.text

        chunk = ms.data_queue.get(timeout=SOCKET_TIMEOUT + send_sleep + 1)
        assert_monitoring_data_payload(chunk.data, regular_payload)

        # No other request (corresponding to the slow client) in the queue.
        with pytest.raises(queue.Empty):
            ms.data_queue.get(timeout=SOCKET_TIMEOUT + send_sleep + 1)
    assert ms.data_queue.empty()


def test_socket_busy_slow_close(
    socket_path: str, relay_id: str, serial: str, agent_receiver: AgentReceiverClient
) -> None:
    """
    If a previous client keeps the socket busy, long enough to cause a timeout,
    then the handler should return 502 Bad Gateway.
    The slow client is quick to connect and send data, but slow when closing its part of the socket.

    Note: cannot make the handler return 502 in this case. Instead, the requests seem to be buffered.
    """

    slow_client_payload = b"slow-payload"
    regular_payload = b"regular-payload"

    monitoring_data = MonitoringData(
        serial=serial,
        host=HOST,
        timestamp=int(time.time()),
        payload=base64.b64encode(regular_payload),
    )

    close_sleep = SOCKET_TIMEOUT + 2

    connection_barrier = threading.Barrier(2, timeout=10)
    send_barrier = threading.Barrier(2, timeout=10)
    close_barrier = threading.Barrier(2, timeout=10)

    with create_socket(socket_path=socket_path, socket_timeout=SOCKET_TIMEOUT) as ms:
        slow_client_thread = threading.Thread(
            target=slow_client_thread_func,
            kwargs={
                "socket_path": socket_path,
                "connection_barrier": connection_barrier,
                "send_barrier": send_barrier,
                "close_barrier": close_barrier,
                "payload": slow_client_payload,
            },
        )
        slow_client_thread.start()
        connection_barrier.wait()

        # At this moment the slow client is connected, but has not sent any data yet.

        # Let the slow client send data
        send_barrier.wait()

        # Do a long sleep (more than SOCKET_TIMEOUT).
        time.sleep(close_sleep)

        # The agent_receiver client sends data, although the slow client is still using the socket.

        response = agent_receiver.forward_monitoring_data(
            relay_id=relay_id,
            monitoring_data=monitoring_data,
        )

        # Let the slow client close.

        close_barrier.wait()
        slow_client_thread.join()

        assert response.status_code == HTTPStatus.NO_CONTENT, response.text

        chunk_1 = ms.data_queue.get(timeout=SOCKET_TIMEOUT + close_sleep + 1)
        assert chunk_1.data == slow_client_payload

        chunk_2 = ms.data_queue.get(timeout=SOCKET_TIMEOUT + close_sleep + 1)
        assert_monitoring_data_payload(chunk_2.data, regular_payload)

    assert ms.data_queue.empty()
    assert chunk_1.socket_id != chunk_2.socket_id


def test_socket_busy_interlaced_send(
    socket_path: str, relay_id: str, serial: str, agent_receiver: AgentReceiverClient
) -> None:
    """
    If a previous client keeps the socket busy, sending data with multiple calls,
    not causing a timeout, the data received by the socket should not be mixed.
    """
    regular_payload = b"regular-payload"
    slow_payload_part_1 = b"abcd"
    slow_payload_part_2 = b"efgh"

    monitoring_data = MonitoringData(
        serial=serial,
        host=HOST,
        timestamp=int(time.time()),
        payload=base64.b64encode(regular_payload),
    )
    part_1_barrier = threading.Barrier(2, timeout=10)
    part_2_barrier = threading.Barrier(2, timeout=10)

    def client_func() -> None:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.connect(socket_path)
            sock.sendall(slow_payload_part_1)
            part_1_barrier.wait()

            part_2_barrier.wait()
            sock.sendall(slow_payload_part_2)
            sock.shutdown(socket.SHUT_RDWR)

    with create_socket(socket_path=socket_path, socket_timeout=SOCKET_TIMEOUT) as ms:
        slow_client_thread = threading.Thread(target=client_func)
        slow_client_thread.start()
        part_1_barrier.wait()

        # The other client has just send the first part of its payload.
        # Now this agent_receiver client will send its payload.

        response = agent_receiver.forward_monitoring_data(
            relay_id=relay_id,
            monitoring_data=monitoring_data,
        )

        # Now let the slow client send the second part of its payload.
        part_2_barrier.wait()
        slow_client_thread.join()

        assert response.status_code == HTTPStatus.NO_CONTENT, response.text

        chunk_1 = ms.data_queue.get(timeout=SOCKET_TIMEOUT + 1)
        chunk_2 = ms.data_queue.get(timeout=SOCKET_TIMEOUT + 1)
        chunk_3 = ms.data_queue.get(timeout=SOCKET_TIMEOUT + 1)

    # the regular payload is postponed until after the slow client has finished sending

    assert chunk_1.data == slow_payload_part_1
    assert chunk_2.data == slow_payload_part_2
    assert chunk_1.socket_id == chunk_2.socket_id

    assert_monitoring_data_payload(chunk_3.data, regular_payload)
    assert chunk_3.socket_id != chunk_1.socket_id


def test_socket_busy_interlaced_send_with_timeout(
    socket_path: str, relay_id: str, serial: str, agent_receiver: AgentReceiverClient
) -> None:
    """
    If a previous client keeps the socket busy, sending data with multiple calls,
    causing a timeout, the data received by the socket should not be mixed.
    """
    regular_payload = b"regular-payload"
    slow_payload_part_1 = b"abcd"
    slow_payload_part_2 = b"efgh"

    monitoring_data = MonitoringData(
        serial=serial,
        host=HOST,
        timestamp=int(time.time()),
        payload=base64.b64encode(regular_payload),
    )
    part_1_barrier = threading.Barrier(2, timeout=10)
    part_2_barrier = threading.Barrier(2, timeout=10)

    def client_func() -> None:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.connect(socket_path)
            sock.sendall(slow_payload_part_1)
            part_1_barrier.wait()

            part_2_barrier.wait()
            try:
                sock.sendall(slow_payload_part_2)
            except BrokenPipeError:
                pass
            sock.shutdown(socket.SHUT_RDWR)

    with create_socket(socket_path=socket_path, socket_timeout=SOCKET_TIMEOUT) as ms:
        slow_client_thread = threading.Thread(target=client_func)
        slow_client_thread.start()
        part_1_barrier.wait()

        # The other client has just send the first part of its payload.
        # Now this agent_receiver client will send its payload.

        response = agent_receiver.forward_monitoring_data(
            relay_id=relay_id,
            monitoring_data=monitoring_data,
        )

        # Do sleep timeout before sending the second part of the payload
        time.sleep(SOCKET_TIMEOUT + 1)

        # Now let the slow client send the second part of its payload.
        part_2_barrier.wait()
        slow_client_thread.join()

        assert response.status_code == HTTPStatus.NO_CONTENT, response.text

        # Only two requests received

        chunk_1 = ms.data_queue.get(timeout=SOCKET_TIMEOUT + 1)
        chunk_2 = ms.data_queue.get(timeout=SOCKET_TIMEOUT + 1)

        with pytest.raises(queue.Empty):
            ms.data_queue.get(timeout=SOCKET_TIMEOUT + 1)

    # The regular payload is postponed until after the slow client has finished sending the first part
    # of the payload. The second part is not received.

    assert chunk_1.data == slow_payload_part_1
    assert_monitoring_data_payload(chunk_2.data, regular_payload)
    assert chunk_1.socket_id != chunk_2.socket_id


def test_connection_refused(
    socket_path: str,
    relay_id: str,
    serial: str,
    agent_receiver: AgentReceiverClient,
) -> None:
    """
    If the socket is not connectable, the handler should be able to deal with the problem.
    """
    with create_non_listening_socket(socket_path=socket_path):
        payload = b"monitoring payload"
        monitoring_data = MonitoringData(
            serial=serial,
            host=HOST,
            timestamp=int(time.time()),
            payload=base64.b64encode(payload),
        )
        response = agent_receiver.forward_monitoring_data(
            relay_id=relay_id,
            monitoring_data=monitoring_data,
        )
        assert response.status_code == HTTPStatus.BAD_GATEWAY, response.text


@pytest.fixture
def relay_id(agent_receiver: AgentReceiverClient, site: SiteMock) -> str:
    relay_name = str(uuid.uuid4())
    _relay_id = RelayID(str(uuid.uuid4()))
    site.set_scenario([], [(_relay_id, OP.ADD)])
    return register_relay(agent_receiver, relay_name, _relay_id)


@pytest.fixture
def socket_path(tmpdir: Path) -> Iterator[str]:
    socket_path = f"{tmpdir}/{secrets.token_urlsafe(8)}-test.sock"
    with patch.object(Config, "raw_data_socket", socket_path):
        yield socket_path


@pytest.fixture
def serial(
    site_context: Config, relay_id: str, agent_receiver: AgentReceiverClient, socket_path: str
) -> str:
    # We use socket_path indirectly; we want to make sure we use the patched the Config class.
    _ = socket_path
    cf = create_config_folder(root=site_context.omd_root, relays=[relay_id])
    agent_receiver.set_serial(cf.serial)
    return cf.serial
