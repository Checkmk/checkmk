#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import uuid
from http import HTTPStatus

import pytest

from cmk.agent_receiver.lib.config import Config
from cmk.relay_protocols.tasks import FetchAdHocTask
from cmk.testlib.agent_receiver.agent_receiver import AgentReceiverClient
from cmk.testlib.agent_receiver.certs import SITE_CN
from cmk.testlib.agent_receiver.config_file_system import create_config_folder
from cmk.testlib.agent_receiver.site_mock import SiteMock


@pytest.mark.parametrize(
    "invalid_cn,description",
    [
        ("", "empty CN"),
        ("wrong-site", "wrong site name"),
        ("Site 'other' local CA", "different site CA"),
    ],
)
def test_create_task_with_various_invalid_cns(
    site: SiteMock,
    agent_receiver: AgentReceiverClient,
    site_context: Config,
    invalid_cn: str,
    description: str,
) -> None:
    """Verify create-task rejects various invalid CN values.

    Expected: 403 Forbidden for all invalid CN values

    This parameterized test covers multiple invalid CN scenarios to ensure
    robust validation.

    Steps:
    1. Start AR with configured relays
    2. Send create-task from localhost with invalid CN
    3. Verify request is rejected with 403
    """
    # Setup: Create relays
    relay_id = str(uuid.uuid4())
    site.set_scenario([relay_id])

    serial_folder = create_config_folder(site_context.omd_root, [relay_id])
    agent_receiver.set_serial(serial_folder.serial)

    # Test: Create task with invalid CN
    with agent_receiver.with_client_ip("127.0.0.1"):
        response = agent_receiver.push_task(
            relay_id=relay_id, spec=FetchAdHocTask(payload=".."), site_cn=invalid_cn
        )

    # Assert: Request is forbidden
    assert response.status_code == HTTPStatus.FORBIDDEN, (
        f"Expected 403 for {description} (CN: {invalid_cn!r}), got {response.status_code}: {response.text}"
    )
    assert "does not match local site CN" in response.text, (
        f"Expected error message for {description}, got: {response.text}"
    )


def test_create_task_with_valid_cn_and_localhost(
    site: SiteMock,
    agent_receiver: AgentReceiverClient,
    site_context: Config,
) -> None:
    """Verify create-task succeeds with correct CN and localhost.

    Expected: 200 OK

    This verifies that valid requests (correct CN + localhost) are accepted.

    Steps:
    1. Start AR with configured relays
    2. Send create-task from localhost with correct site CN
    3. Verify request succeeds
    """
    # Setup: Create relays
    relay_id_a = str(uuid.uuid4())
    relay_id_b = str(uuid.uuid4())
    site.set_scenario([relay_id_a, relay_id_b])

    serial_folder = create_config_folder(site_context.omd_root, [relay_id_a, relay_id_b])
    agent_receiver.set_serial(serial_folder.serial)

    # Test: Create task with correct CN from localhost
    with agent_receiver.with_client_ip("127.0.0.1"):
        response = agent_receiver.push_task(
            relay_id=relay_id_a, spec=FetchAdHocTask(payload=".."), site_cn=SITE_CN
        )
    # Assert: Request succeeds
    assert response.status_code == HTTPStatus.OK, response.text


def test_create_task_cn_check_without_localhost(
    site: SiteMock,
    agent_receiver: AgentReceiverClient,
    site_context: Config,
) -> None:
    """Verify create-task requires localhost even with valid CN.

    Expected: 403 Forbidden (localhost check fails first)

    Both localhost and CN checks must pass. This verifies that even with
    a valid CN, requests from non-localhost are rejected.

    Steps:
    1. Start AR with configured relays
    2. Send activate-config from non-localhost IP with correct CN
    3. Verify request is rejected (localhost validation fails first)
    """
    # Setup: Create relays
    relay_id = str(uuid.uuid4())
    site.set_scenario([relay_id])

    serial_folder = create_config_folder(site_context.omd_root, [relay_id])
    agent_receiver.set_serial(serial_folder.serial)

    # Test: Create task with correct CN but from non-localhost
    with agent_receiver.with_client_ip("192.168.1.100"):
        response = agent_receiver.push_task(
            relay_id=relay_id, spec=FetchAdHocTask(payload=".."), site_cn=SITE_CN
        )

    # Assert: Request is forbidden (localhost check fails)
    assert response.status_code == HTTPStatus.FORBIDDEN, response.text
    assert "Request must originate from localhost" in response.text
