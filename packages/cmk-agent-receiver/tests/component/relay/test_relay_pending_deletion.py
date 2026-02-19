#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Component tests for relay behavior during PENDING_DELETION state."""

from __future__ import annotations

import base64
import logging
import secrets
import time
import uuid
from collections.abc import Iterator
from http import HTTPStatus
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest

from cmk.agent_receiver.lib.config import Config
from cmk.agent_receiver.relay.lib.shared_types import RelayID
from cmk.relay_protocols.monitoring_data import MonitoringData
from cmk.relay_protocols.relays import RelayRefreshCertResponse, RelayState, RelayStatusResponse
from cmk.relay_protocols.tasks import (
    FetchAdHocTask,
    ResultType,
    TaskResponse,
    TaskStatus,
)
from cmk.testlib.agent_receiver import certs as certslib
from cmk.testlib.agent_receiver.agent_receiver import AgentReceiverClient, register_relay
from cmk.testlib.agent_receiver.config_file_system import ConfigFolder, create_config_folder
from cmk.testlib.agent_receiver.mock_socket import create_socket
from cmk.testlib.agent_receiver.site_mock import OP, SiteMock, User
from cmk.testlib.agent_receiver.tasks import get_relay_tasks, push_task

HOST = "testhost"
TEST_SOCKET_TIMEOUT = 2.0
MONITORING_PAYLOAD = b"monitoring payload"


@pytest.fixture
def site_client(site: SiteMock, user: User) -> httpx.Client:
    return httpx.Client(
        base_url=site.base_url,
        headers={
            "Content-Type": "application/json",
            "Authorization": user.bearer,
        },
    )


@pytest.fixture
def relay_in_pending_deletion(
    site: SiteMock,
    site_client: httpx.Client,
    agent_receiver: AgentReceiverClient,
    site_context: Config,
    site_name: str,
) -> Iterator[tuple[RelayID, ConfigFolder]]:
    """Set up a relay that is registered, activated, fully operational, then put into
    PENDING_DELETION by deleting it from the site without activating the change.

    Yields the relay_id and the config folder so callers can build MonitoringData
    or run further assertions.
    """
    relay_id = RelayID(str(uuid.uuid4()))
    site.set_scenario(relays=[], changes=[(relay_id, OP.ADD), (relay_id, OP.DEL)])

    # Register relay and create config folder
    register_relay(agent_receiver, "test_relay", relay_id)
    serial_folder = create_config_folder(site_context.omd_root, [relay_id])
    agent_receiver.set_serial(serial_folder.serial)

    # Activate config - relay is operating normally
    with agent_receiver.with_client_ip("127.0.0.1"):
        resp = agent_receiver.activate_config(site_cn=site_name)
    assert resp.status_code == HTTPStatus.OK, resp.text

    # Relay completes its config task (fully operational)
    pending = get_relay_tasks(agent_receiver, relay_id, status="PENDING")
    assert len(pending.tasks) == 1
    resp = agent_receiver.update_task(
        relay_id=relay_id,
        task_id=pending.tasks[0].id,
        result_type="OK",
        result_payload="Config applied",
    )
    assert resp.status_code < 400, resp.text

    # Delete relay from site without activating the deletion change
    site_client.delete(f"/objects/relay/{relay_id}")

    # Verify PENDING_DELETION
    status_resp = agent_receiver.get_relay_status(relay_id)
    assert status_resp.status_code == HTTPStatus.OK, status_resp.text
    status = RelayStatusResponse.model_validate_json(status_resp.text)
    assert status.state == RelayState.PENDING_DELETION

    yield relay_id, serial_folder


def _make_monitoring_data(serial: int) -> MonitoringData:
    """Build a MonitoringData payload matching the relay engine's submit_data call."""
    return MonitoringData(
        serial=serial,
        host=HOST,
        service="Check_MK",
        timestamp=int(time.time()),
        payload=base64.b64encode(MONITORING_PAYLOAD),
    )


def _assert_no_errors_in_logs(site_context: Config) -> None:
    """Verify the agent-receiver has not logged any ERROR-level entries."""
    for handler in logging.getLogger("agent-receiver").handlers:
        handler.flush()
    log_content = site_context.log_path.read_text()
    error_lines = [line for line in log_content.splitlines() if " ERROR " in line]
    assert not error_lines, "Unexpected ERROR entries in agent-receiver log:\n" + "\n".join(
        error_lines
    )


def _assert_agent_receiver_healthy(agent_receiver: AgentReceiverClient) -> None:
    """Verify the agent-receiver is still responsive via its health endpoint."""
    resp = agent_receiver.client.get(f"/{agent_receiver.site_name}/agent-receiver/openapi.json")
    assert resp.status_code == HTTPStatus.OK, f"Health check failed: {resp.status_code}"


def test_relay_pending_deletion_submit_data_ok(
    relay_in_pending_deletion: tuple[RelayID, ConfigFolder],
    agent_receiver: AgentReceiverClient,
    site_context: Config,
    tmpdir: Path,
) -> None:
    """Verify that a relay in PENDING_DELETION can still push monitoring data successfully.

    Simulates the relay engine's submit_data (POST /{relay_id}/monitoring) reaching a
    working monitoring socket.  Expects HTTP 204 NO_CONTENT (OK).

    Test steps:
    1. Relay is in PENDING_DELETION (via fixture)
    2. Relay calls submit_data - monitoring socket is available
    3. Assert agent-receiver returns 204 NO_CONTENT
    4. Assert agent-receiver is still healthy and logs contain no errors
    """
    relay_id, serial_folder = relay_in_pending_deletion
    monitoring_data = _make_monitoring_data(serial_folder.serial.value)

    socket_path = f"{tmpdir}/{secrets.token_urlsafe(8)}.sock"
    with patch.object(Config, "raw_data_socket", socket_path):
        with create_socket(socket_path=socket_path, socket_timeout=TEST_SOCKET_TIMEOUT) as ms:
            resp = agent_receiver.forward_monitoring_data(
                relay_id=relay_id,
                monitoring_data=monitoring_data,
            )
            connection_data = ms.data_queue.get(timeout=TEST_SOCKET_TIMEOUT)
    assert resp.status_code == HTTPStatus.NO_CONTENT, resp.text
    _, received_payload = connection_data.data.split(b"\n", 1)
    assert received_payload == MONITORING_PAYLOAD

    _assert_agent_receiver_healthy(agent_receiver)
    _assert_no_errors_in_logs(site_context)


def test_relay_pending_deletion_get_relay_tasks(
    relay_in_pending_deletion: tuple[RelayID, ConfigFolder],
    agent_receiver: AgentReceiverClient,
    site_context: Config,
) -> None:
    """Verify that a relay in PENDING_DELETION can still retrieve its task list.

    get_relay_tasks does not query the CMK API; it uses the local config only, so
    the relay must be able to fetch its tasks even after deletion from the site.

    Test steps:
    1. Relay is in PENDING_DELETION (via fixture)
    2. Relay calls get_relay_tasks
    3. Assert agent-receiver returns 200 OK with the task list
    4. Assert agent-receiver is still healthy and logs contain no errors
    """
    relay_id, _ = relay_in_pending_deletion

    tasks_resp = agent_receiver.get_relay_tasks(relay_id)
    assert tasks_resp.status_code == HTTPStatus.OK, tasks_resp.text

    _assert_agent_receiver_healthy(agent_receiver)
    _assert_no_errors_in_logs(site_context)


def test_relay_pending_deletion_refresh_cert(
    relay_in_pending_deletion: tuple[RelayID, ConfigFolder],
    agent_receiver: AgentReceiverClient,
    site_context: Config,
) -> None:
    """Verify that a relay in PENDING_DELETION can still refresh its certificate.

    The relay may need to rotate its certificate while waiting for the deletion
    change to be activated.  The agent-receiver must allow cert refresh for any
    relay it knows about locally, regardless of the CMK API state.

    Test steps:
    1. Relay is in PENDING_DELETION (via fixture)
    2. Relay calls refresh_cert endpoint
    3. Assert agent-receiver returns 200 OK
    4. Assert the returned certificate has the correct relay_id as CN
    5. Assert agent-receiver is still healthy and logs contain no errors
    """
    relay_id, _ = relay_in_pending_deletion

    resp = agent_receiver.refresh_cert(relay_id)
    assert resp.status_code == HTTPStatus.OK, resp.text

    refresh_response = RelayRefreshCertResponse.model_validate_json(resp.text)
    cert = certslib.read_certificate(refresh_response.client_cert)
    assert certslib.check_cn(cert, relay_id)

    _assert_agent_receiver_healthy(agent_receiver)
    _assert_no_errors_in_logs(site_context)


def test_relay_pending_deletion_with_fetch_adhoc_task(
    relay_in_pending_deletion: tuple[RelayID, ConfigFolder],
    agent_receiver: AgentReceiverClient,
    site_context: Config,
    site_name: str,
) -> None:
    """Verify agent-receiver handles FetchAdHocTask results when relay is PENDING_DELETION.

    NOTE: This is a secondary, component-level edge case.  In real deployments all
    hosts must be removed from a relay before it can be deleted, so FetchAdHocTask
    items should never be pending at deletion time.  This test validates that the
    agent-receiver handles this case correctly at the component level in isolation.

    Test steps:
    1. Relay is in PENDING_DELETION (via fixture)
    2. Push a FetchAdHocTask and relay reports OK - assert task is FINISHED
    3. Push another FetchAdHocTask and relay reports ERROR - assert task is FAILED
    4. Assert agent-receiver is still healthy and logs contain no errors
    """
    relay_id, _ = relay_in_pending_deletion

    # Push a task and relay reports OK
    ok_task = push_task(
        agent_receiver,
        relay_id,
        FetchAdHocTask(payload="fetch host data"),
        site_name,
    )
    ok_resp = agent_receiver.update_task(
        relay_id=relay_id,
        task_id=ok_task.task_id,
        result_type="OK",
        result_payload="Host data fetched",
    )
    assert ok_resp.status_code < 400, ok_resp.text
    ok_result = TaskResponse.model_validate(ok_resp.json())
    assert ok_result.status == TaskStatus.FINISHED
    assert ok_result.result_type == ResultType.OK

    # Push a task and relay reports ERROR
    error_task = push_task(
        agent_receiver,
        relay_id,
        FetchAdHocTask(payload="fetch host data again"),
        site_name,
    )
    error_resp = agent_receiver.update_task(
        relay_id=relay_id,
        task_id=error_task.task_id,
        result_type="ERROR",
        result_payload="Host unreachable",
    )
    assert error_resp.status_code < 400, error_resp.text
    error_result = TaskResponse.model_validate(error_resp.json())
    assert error_result.status == TaskStatus.FAILED
    assert error_result.result_type == ResultType.ERROR

    _assert_agent_receiver_healthy(agent_receiver)
    _assert_no_errors_in_logs(site_context)
