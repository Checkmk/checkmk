#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
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
    create_non_listening_socket,
    create_socket,
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
        chunk = ms.data_queue.get(timeout=TEST_SOCKET_TIMEOUT)
        lines = chunk.data.splitlines()
        assert lines[0].decode() == expected_header
        assert lines[1] == payload


def test_forward_monitoring_data_with_delay(
    socket_path: str,
    relay_id: str,
    serial: Serial,
    agent_receiver: AgentReceiverClient,
) -> None:
    """
    If the socket is slower in accepting data, the data can still be forwarded.
    Note: the configured socket timeouts don't seem to have an effect (on UNIX sockets at least).
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
        chunk = ms.data_queue.get(timeout=TEST_SOCKET_TIMEOUT + delay + 1)
        assert_monitoring_data_payload(chunk.data, payload)


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
    lines = received_data.splitlines()
    assert len(lines) == 2, f"Expected 2 lines (header + payload), got {len(lines)}"
    received_payload = lines[1]
    assert received_payload == expected_payload


def test_connection_refused(
    socket_path: str,
    relay_id: str,
    serial: Serial,
    agent_receiver: AgentReceiverClient,
) -> None:
    """
    If the socket is not connectable, the handler should be able to deal with the problem.
    """
    payload = b"monitoring payload"
    monitoring_data = create_monitoring_data(serial, payload)

    with create_non_listening_socket(socket_path=socket_path):
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
) -> Serial:
    # We use socket_path indirectly; we want to make sure we use the patched the Config class.
    _ = socket_path
    cf = create_config_folder(root=site_context.omd_root, relays=[relay_id])
    agent_receiver.set_serial(cf.serial)
    return cf.serial
