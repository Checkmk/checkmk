#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import base64
import secrets
import time
import uuid
from collections.abc import Iterator
from http import HTTPStatus
from pathlib import Path
from unittest.mock import patch

import pytest

from cmk.agent_receiver.lib.config import Config
from cmk.agent_receiver.relay.lib.shared_types import RelayID, Serial
from cmk.relay_protocols.monitoring_data import MonitoringData
from cmk.testlib.agent_receiver.agent_receiver import AgentReceiverClient, register_relay
from cmk.testlib.agent_receiver.config_file_system import create_config_folder
from cmk.testlib.agent_receiver.mock_socket import (
    create_crashy_socket,
    create_non_listening_socket,
    create_socket,
    create_unresponsive_socket,
)
from cmk.testlib.agent_receiver.site_mock import OP, SiteMock

HOST = "testhost"
# Test timeout - should match the override in conftest.py
# Production uses 5.0s, tests use 2.0s for faster execution
TEST_SOCKET_TIMEOUT = 2.0
TIMEOUT_MARGIN = 1  # Safety margin for timeout calculations


@pytest.mark.parametrize("service_name", ["Check_MK", "TestCase"])
def test_forward_monitoring_data(
    socket_path: str,
    relay_id: str,
    serial: Serial,
    agent_receiver: AgentReceiverClient,
    service_name: str,
) -> None:
    """Verify that monitoring data is correctly forwarded to the socket with proper header and payload formatting.

    Test steps:
    1. Create monitoring data with payload and service name
    2. Forward data to agent receiver
    3. Verify header and payload are correctly received at socket
    """
    payload = b"monitoring payload"
    timestamp = int(time.time())
    expected_header = (
        f"payload_type:fetcher;"
        f"payload_size:{len(payload)};"
        f"config_serial:{serial};"
        f"start_timestamp:{timestamp};"
        f"host_by_name:{HOST};"
        f"service_description:{service_name};"
    )
    with create_socket(socket_path=socket_path, socket_timeout=TEST_SOCKET_TIMEOUT) as ms:
        monitoring_data = create_monitoring_data(serial, payload, service_name)
        response = agent_receiver.forward_monitoring_data(
            relay_id=relay_id,
            monitoring_data=monitoring_data,
        )
        assert response.status_code == HTTPStatus.NO_CONTENT
        connection_data = ms.data_queue.get(timeout=TEST_SOCKET_TIMEOUT)
        parts = connection_data.data.split(b"\n", 1)
        assert parts[0].decode() == expected_header
        assert parts[1] == payload


def test_forward_monitoring_data_huge_payload(
    socket_path: str,
    relay_id: str,
    serial: Serial,
    agent_receiver: AgentReceiverClient,
) -> None:
    """Verify that large payloads exceeding the socket buffer size are successfully transmitted without data loss.

    Test steps:
    1. Generate large payload (256KB) exceeding socket buffer
    2. Forward data to agent receiver
    3. Verify complete payload is received correctly
    """
    # Generate payload without newlines to avoid complicating the header/payload split
    # Keep generating until we get a payload without newlines (very rare to have \n in random bytes)
    payload = secrets.token_bytes(128 * 1024 * 2)  # 256KB - exceeds typical socket buffer
    payload = payload.replace(b"\n", b"")
    service_name = "Check_MK"
    monitoring_data = create_monitoring_data(serial, payload, service_name)

    with create_socket(socket_path=socket_path, socket_timeout=TEST_SOCKET_TIMEOUT) as ms:
        response = agent_receiver.forward_monitoring_data(
            relay_id=relay_id,
            monitoring_data=monitoring_data,
        )
        assert response.status_code == HTTPStatus.NO_CONTENT

        # Get the aggregated data from the connection
        connection_data = ms.data_queue.get(timeout=TEST_SOCKET_TIMEOUT + 1)

        # Split on first newline only (payload is binary and may contain line separator bytes)
        parts = connection_data.data.split(b"\n", 1)
        assert len(parts) == 2, f"Expected 2 parts (header + payload), got {len(parts)}"

        received_header = parts[0].decode()
        received_payload = parts[1]

        # Verify header contains correct metadata
        assert "payload_type:fetcher;" in received_header
        assert f"payload_size:{len(payload)};" in received_header
        assert f"config_serial:{serial};" in received_header
        assert f"host_by_name:{HOST};" in received_header
        assert f"service_description:{service_name};" in received_header

        # Verify payload matches exactly
        assert received_payload == payload, (
            f"Expected {len(payload)} bytes, got {len(received_payload)} bytes"
        )


def test_forward_monitoring_data_with_delay(
    socket_path: str,
    relay_id: str,
    serial: Serial,
    agent_receiver: AgentReceiverClient,
) -> None:
    """Verify that data can still be forwarded successfully even when the socket is slower in accepting data.

    Test steps:
    1. Create socket with delay exceeding timeout
    2. Forward monitoring data to agent receiver
    3. Verify data is successfully received despite delay
    """
    delay = TEST_SOCKET_TIMEOUT + TIMEOUT_MARGIN
    payload = b"monitoring payload"
    monitoring_data = create_monitoring_data(serial, payload)

    with create_socket(
        socket_path=socket_path, socket_timeout=TEST_SOCKET_TIMEOUT, delay=delay
    ) as ms:
        response = agent_receiver.forward_monitoring_data(
            relay_id=relay_id,
            monitoring_data=monitoring_data,
        )
        assert response.status_code == HTTPStatus.NO_CONTENT, response.text
        connection_data = ms.data_queue.get(timeout=TEST_SOCKET_TIMEOUT + delay + 1)
        assert_monitoring_data_payload(connection_data.data, payload)


def create_monitoring_data(
    serial: Serial, payload: bytes, service: str = "Check_MK"
) -> MonitoringData:
    """Helper to create MonitoringData with consistent defaults."""
    return MonitoringData(
        serial=serial.value,
        host=HOST,
        service=service,
        timestamp=int(time.time()),
        payload=base64.b64encode(payload),
    )


def assert_monitoring_data_payload(received_data: bytes, expected_payload: bytes) -> None:
    parts = received_data.split(b"\n", 1)
    assert len(parts) == 2, f"Expected 2 parts (header + payload), got {len(parts)}"
    received_payload = parts[1]
    assert received_payload == expected_payload


def test_connection_refused(
    socket_path: str,
    relay_id: str,
    serial: Serial,
    agent_receiver: AgentReceiverClient,
) -> None:
    """Verify that connection refused errors (ECONNREFUSED) are handled correctly and return a 502 BAD_GATEWAY response.

    Test steps:
    1. Create socket without accepting connections
    2. Attempt to forward monitoring data
    3. Verify 502 BAD_GATEWAY response is returned
    """
    payload = b"monitoring payload"
    monitoring_data = create_monitoring_data(serial, payload)

    with create_non_listening_socket(socket_path=socket_path):
        response = agent_receiver.forward_monitoring_data(
            relay_id=relay_id,
            monitoring_data=monitoring_data,
        )
        assert response.status_code == HTTPStatus.BAD_GATEWAY, response.text


def test_socket_path_not_exists(
    relay_id: str,
    serial: Serial,
    agent_receiver: AgentReceiverClient,
    tmpdir: Path,
) -> None:
    """Verify that missing socket path errors (ENOENT) are handled correctly and return a 502 BAD_GATEWAY response.

    Test steps:
    1. Configure nonexistent socket path
    2. Attempt to forward monitoring data
    3. Verify 502 BAD_GATEWAY response is returned
    """
    payload = b"monitoring payload"
    monitoring_data = create_monitoring_data(serial, payload)

    # Use a socket path that doesn't exist
    nonexistent_socket = f"{tmpdir}/nonexistent-{secrets.token_urlsafe(8)}.sock"

    with patch.object(Config, "raw_data_socket", nonexistent_socket):
        response = agent_receiver.forward_monitoring_data(
            relay_id=relay_id,
            monitoring_data=monitoring_data,
        )
        assert response.status_code == HTTPStatus.BAD_GATEWAY, response.text


def test_sendall_timeout_unresponsive_server(
    socket_path: str,
    relay_id: str,
    serial: Serial,
    agent_receiver: AgentReceiverClient,
) -> None:
    """Verify that sendall() timeout with an unresponsive server is handled correctly and returns a 502 BAD_GATEWAY response.

    Test steps:
    1. Create unresponsive socket that accepts but never receives
    2. Forward large payload that exceeds socket buffer
    3. Verify 502 BAD_GATEWAY response after timeout
    """
    # Large payload that will exceed socket send buffer (typically 64KB-128KB)
    # Using 256kb to ensure it blocks waiting for the server to recv()
    payload = secrets.token_bytes(256 * 1024)
    monitoring_data = create_monitoring_data(serial, payload)

    with create_unresponsive_socket(socket_path=socket_path):
        response = agent_receiver.forward_monitoring_data(
            relay_id=relay_id,
            monitoring_data=monitoring_data,
        )
        assert response.status_code == HTTPStatus.BAD_GATEWAY, response.text
        assert "Failed to forward monitoring data" in response.text


def test_broken_pipe_during_send(
    socket_path: str,
    relay_id: str,
    serial: Serial,
    agent_receiver: AgentReceiverClient,
) -> None:
    """Verify that broken pipe errors (EPIPE) during send are handled correctly and return a 502 BAD_GATEWAY response.

    Test steps:
    1. Create socket that accepts then immediately closes connection
    2. Forward large payload to trigger broken pipe
    3. Verify 502 BAD_GATEWAY response is returned
    """
    # Use a large payload (256KB) to ensure sendall() doesn't complete instantly.
    # Small payloads fit entirely in the socket send buffer, making it impossible
    # to reliably trigger EPIPE during transmission.
    payload = secrets.token_bytes(256 * 1024)
    monitoring_data = create_monitoring_data(serial, payload)

    with create_crashy_socket(socket_path=socket_path):
        response = agent_receiver.forward_monitoring_data(
            relay_id=relay_id,
            monitoring_data=monitoring_data,
        )
        assert response.status_code == HTTPStatus.BAD_GATEWAY, response.text
        assert "Failed to forward monitoring data" in response.text


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
) -> Serial:
    # We use socket_path indirectly; we want to make sure we use the patched the Config class.
    _ = socket_path
    cf = create_config_folder(root=site_context.omd_root, relays=[relay_id])
    agent_receiver.set_serial(cf.serial)
    return cf.serial
