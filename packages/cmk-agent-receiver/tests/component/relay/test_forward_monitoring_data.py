#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import base64
import secrets
import time
import uuid
from http import HTTPStatus

import httpx2
import pytest
from fastapi.testclient import TestClient

from cmk.agent_receiver.lib.config import Config
from cmk.agent_receiver.lib.mtls_auth_validator import (
    INJECTED_ISSUER_HEADER,
    INJECTED_SERIAL_HEADER,
    INJECTED_UUID_HEADER,
)
from cmk.agent_receiver.relay.lib.shared_types import RelayID, Serial
from cmk.relay_protocols.monitoring_data import MonitoringData, PayloadType
from cmk.testlib.agent_receiver.certs import relay_ca_common_name, UNREVOKED_SERIAL_NUMBER
from cmk.testlib.agent_receiver.clients import (
    RelayClient,
    RelayRegistrationClient,
)
from cmk.testlib.agent_receiver.mock_socket import (
    create_busy_socket,
    create_socket,
)
from cmk.testlib.agent_receiver.relay_config_generator import RelayConfig
from cmk.testlib.agent_receiver.site_mock import OP, SiteMock, User

HOST = "testhost"
# Test timeout - should match the override in conftest.py
# Production uses 5.0s, tests use 2.0s for faster execution
TEST_SOCKET_TIMEOUT = 2.0
TIMEOUT_MARGIN = 1  # Safety margin for timeout calculations


@pytest.mark.parametrize("service_name", ["Check_MK", "TestCase"])
def test_forward_monitoring_data(
    socket_path: str,
    relay_id: str,
    relay_config: RelayConfig,
    test_client: TestClient,
    site: SiteMock,
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
        f"config_serial:{relay_config.serial};"
        f"relay_id:{relay_id};"
        f"start_timestamp:{timestamp};"
        f"host_by_name:{HOST};"
        f"service_description:{service_name};"
    )
    with create_socket(socket_path=socket_path, socket_timeout=TEST_SOCKET_TIMEOUT) as ms:
        monitoring_data = create_monitoring_data(relay_config.serial, payload, service_name)
        relay = RelayClient(test_client, site.site_name, relay_id)
        relay.apply_config(relay_config)
        response = relay.forward_monitoring_data(monitoring_data)
        assert response.status_code == HTTPStatus.NO_CONTENT
        connection_data = ms.data_queue.get(timeout=TEST_SOCKET_TIMEOUT)
        parts = connection_data.data.split(b"\n", 1)
        assert parts[0].decode() == expected_header
        assert parts[1] == payload


def test_forward_monitoring_data_huge_payload(
    socket_path: str,
    relay_id: str,
    relay_config: RelayConfig,
    test_client: TestClient,
    site: SiteMock,
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
    monitoring_data = create_monitoring_data(relay_config.serial, payload, service_name)

    with create_socket(socket_path=socket_path, socket_timeout=TEST_SOCKET_TIMEOUT) as ms:
        relay = RelayClient(test_client, site.site_name, relay_id)
        relay.apply_config(relay_config)
        response = relay.forward_monitoring_data(monitoring_data)
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
        assert f"config_serial:{relay_config.serial};" in received_header
        assert f"relay_id:{relay_id};" in received_header
        assert f"host_by_name:{HOST};" in received_header
        assert f"service_description:{service_name};" in received_header

        # Verify payload matches exactly
        assert received_payload == payload, (
            f"Expected {len(payload)} bytes, got {len(received_payload)} bytes"
        )


def test_forward_monitoring_data_with_delay(
    socket_path: str,
    relay_id: str,
    relay_config: RelayConfig,
    test_client: TestClient,
    site: SiteMock,
) -> None:
    """Verify that data can still be forwarded successfully even when the socket is slower in accepting data.

    Test steps:
    1. Create socket with delay exceeding timeout
    2. Forward monitoring data to agent receiver
    3. Verify data is successfully received despite delay
    """
    delay = TEST_SOCKET_TIMEOUT + TIMEOUT_MARGIN
    payload = b"monitoring payload"
    monitoring_data = create_monitoring_data(relay_config.serial, payload)

    with create_socket(
        socket_path=socket_path, socket_timeout=TEST_SOCKET_TIMEOUT, delay=delay
    ) as ms:
        relay = RelayClient(test_client, site.site_name, relay_id)
        relay.apply_config(relay_config)
        response = relay.forward_monitoring_data(monitoring_data)
        assert response.status_code == HTTPStatus.NO_CONTENT, response.text
        connection_data = ms.data_queue.get(timeout=TEST_SOCKET_TIMEOUT + delay + 1)
        assert_monitoring_data_payload(connection_data.data, payload)


def test_forward_is_answered_before_the_core_accepts_it(
    socket_path: str,
    relay_id: str,
    relay_config: RelayConfig,
    test_client: TestClient,
    site: SiteMock,
) -> None:
    """A stalled core must not hold up the relay: it gets its answer once the data is queued."""
    payload = b"monitoring payload"
    monitoring_data = create_monitoring_data(relay_config.serial, payload)
    relay = RelayClient(test_client, site.site_name, relay_id)
    relay.apply_config(relay_config)

    with create_busy_socket(socket_path=socket_path, busy_for=1.0) as ms:
        response = relay.forward_monitoring_data(monitoring_data)
        nothing_arrived_yet = ms.data_queue.empty()
        connection_data = ms.data_queue.get(timeout=TEST_SOCKET_TIMEOUT)

    assert response.status_code == HTTPStatus.NO_CONTENT, response.text
    assert nothing_arrived_yet
    assert_monitoring_data_payload(connection_data.data, payload)


def test_forward_active_check_data_announces_it_as_an_active_check(
    socket_path: str,
    relay_id: str,
    relay_config: RelayConfig,
    test_client: TestClient,
    site: SiteMock,
) -> None:
    """An active-check result must be announced to the core as such.

    The core reads the payload type from the header and routes the payload
    accordingly, so a result announced as a fetcher payload would be parsed as
    agent output.
    """
    payload = b"000\n0000000f\ntesthost\tOK - all good"
    with create_socket(socket_path=socket_path, socket_timeout=TEST_SOCKET_TIMEOUT) as ms:
        monitoring_data = create_monitoring_data(
            relay_config.serial, payload, payload_type=PayloadType.ACTIVE_CHECK
        )
        relay = RelayClient(test_client, site.site_name, relay_id)
        relay.apply_config(relay_config)

        response = relay.forward_monitoring_data(monitoring_data)

        assert response.status_code == HTTPStatus.NO_CONTENT
        connection_data = ms.data_queue.get(timeout=TEST_SOCKET_TIMEOUT)
        header, forwarded = connection_data.data.split(b"\n", 1)
        assert "payload_type:active_check;" in header.decode(), header
        assert forwarded == payload


def create_monitoring_data(
    serial: Serial,
    payload: bytes,
    service: str = "Check_MK",
    payload_type: PayloadType = PayloadType.FETCHER,
) -> MonitoringData:
    """Helper to create MonitoringData with consistent defaults."""
    return MonitoringData(
        serial=serial.value,
        host=HOST,
        service=service,
        timestamp=int(time.time()),
        payload=base64.b64encode(payload),
        payload_type=payload_type,
    )


def assert_monitoring_data_payload(received_data: bytes, expected_payload: bytes) -> None:
    parts = received_data.split(b"\n", 1)
    assert len(parts) == 2, f"Expected 2 parts (header + payload), got {len(parts)}"
    received_payload = parts[1]
    assert received_payload == expected_payload


@pytest.mark.parametrize(
    "malformed_service",
    [
        pytest.param(
            "Check_MK;\npayload_type:fetcher;host_by_name:testit;",
            id="newline_splits_header",
        ),
        pytest.param(
            "Check_MK\nfake_header:value;",
            id="bare_newline",
        ),
        pytest.param(
            "Check_MK;host_by_name:somethine;",
            id="semicolon_injects_field",
        ),
        pytest.param(
            "Check_MK;payload_size:0;",
            id="semicolon_overrides_size",
        ),
    ],
)
def test_malformed_service_name_is_rejected(
    socket_path: str,
    relay_id: str,
    relay_config: RelayConfig,
    test_client: TestClient,
    site: SiteMock,
    malformed_service: str,
) -> None:
    """Malformed message are silently dropped by the cmc.
    Rather reject openly then silently drop in the cmc forwarding.

    Test steps:
    1. Create monitoring data with a service name containing newline characters
    2. Forward data to agent receiver
    3. Verify the request is rejected with 422 Unprocessable Entity
    """
    with create_socket(socket_path=socket_path, socket_timeout=TEST_SOCKET_TIMEOUT):
        response = _post_raw_monitoring_data(
            test_client, site.site_name, relay_id, relay_config.serial, service=malformed_service
        )
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def _post_raw_monitoring_data(
    test_client: TestClient,
    site_name: str,
    relay_id: str,
    serial: Serial,
    service: str,
    payload: bytes = b"monitoring payload",
) -> httpx2.Response:
    """Post monitoring data as raw JSON, bypassing client-side Pydantic validation."""
    return raw_post(
        test_client,
        f"/{site_name}/relays/{relay_id}/monitoring",
        json={
            "serial": serial.value,
            "host": HOST,
            "service": service,
            "timestamp": int(time.time()),
            "payload": base64.b64encode(payload).decode(),
        },
        identity_cn=relay_id,
        issuer_cn=relay_ca_common_name(site_name),
    )


@pytest.fixture
def relay_id(test_client: TestClient, user: User, site: SiteMock) -> str:
    relay_name = str(uuid.uuid4())
    relay_id = RelayID(str(uuid.uuid4()))
    site.set_scenario([], [(relay_id, OP.ADD)])
    RelayRegistrationClient(test_client, site.site_name).register(relay_name, relay_id, user)
    return relay_id


@pytest.fixture
def socket_path(site_context: Config) -> str:
    site_context.raw_data_socket.parent.mkdir(parents=True, exist_ok=True)
    return str(site_context.raw_data_socket)


@pytest.fixture
def relay_config(site: SiteMock, relay_id: str) -> RelayConfig:
    return site.push_config([relay_id])


def raw_post(
    http: TestClient,
    path: str,
    *,
    json: object,
    identity_cn: str,
    issuer_cn: str,
) -> httpx2.Response:
    return http.post(
        path,
        headers={
            INJECTED_UUID_HEADER: identity_cn,
            INJECTED_ISSUER_HEADER: issuer_cn,
            INJECTED_SERIAL_HEADER: UNREVOKED_SERIAL_NUMBER,
        },
        json=json,
    )
