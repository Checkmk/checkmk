#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Tests for get-task endpoint authorization (localhost + CN validation)."""

from __future__ import annotations

import uuid
from http import HTTPStatus

import pytest

from cmk.agent_receiver.lib.config import Config
from cmk.testlib.agent_receiver.agent_receiver import AgentReceiverClient
from cmk.testlib.agent_receiver.config_file_system import create_config_folder
from cmk.testlib.agent_receiver.site_mock import SiteMock
from cmk.testlib.agent_receiver.tasks import add_tasks


@pytest.mark.parametrize(
    "invalid_cn,description",
    [
        ("missing: no client certificate provided", "TLS connection without client cert"),
        ("", "empty CN"),
        ("wrongsite", "different cert CN"),
    ],
)
def test_get_task_with_various_invalid_cns(
    site: SiteMock,
    agent_receiver: AgentReceiverClient,
    site_context: Config,
    invalid_cn: str,
    description: str,
) -> None:
    """Verify get-task rejects various invalid CN values.

    Expected: 403 Forbidden for all invalid CN values

    Steps:
    1. Start AR with configured relays
    2. Send get-task from localhost with invalid CN
    3. Verify request is rejected with 403
    """
    relay_id = str(uuid.uuid4())
    site.set_scenario([relay_id])

    serial_folder = create_config_folder(site_context.omd_root, [relay_id])
    agent_receiver.set_serial(serial_folder.serial)

    with agent_receiver.with_client_ip("127.0.0.1"):
        response = agent_receiver.get_task(
            relay_id=relay_id,
            task_id=str(uuid.uuid4()),
            site_cn=invalid_cn,
        )

    assert response.status_code == HTTPStatus.FORBIDDEN, (
        f"Expected 403 for {description} (CN: {invalid_cn!r}), got {response.status_code}: {response.text}"
    )
    assert "does not match local site CN" in response.text, (
        f"Expected error message for {description}, got: {response.text}"
    )


def test_get_task_with_valid_cn_and_localhost(
    site: SiteMock,
    agent_receiver: AgentReceiverClient,
    site_context: Config,
    site_name: str,
) -> None:
    """Verify get-task succeeds with correct CN and localhost.

    Expected: 200 OK

    Steps:
    1. Start AR with configured relays and create a task
    2. Send get-task from localhost with correct site CN
    3. Verify request succeeds
    """
    relay_id = str(uuid.uuid4())
    site.set_scenario([relay_id])

    serial_folder = create_config_folder(site_context.omd_root, [relay_id])
    agent_receiver.set_serial(serial_folder.serial)

    task_ids = add_tasks(1, agent_receiver, relay_id, site_name)
    task_id = str(task_ids[0])

    with agent_receiver.with_client_ip("127.0.0.1"):
        response = agent_receiver.get_task(
            relay_id=relay_id,
            task_id=task_id,
            site_cn=site_name,
        )

    assert response.status_code == HTTPStatus.OK, response.text


def test_get_task_cn_check_without_localhost(
    site: SiteMock,
    agent_receiver: AgentReceiverClient,
    site_context: Config,
    site_name: str,
) -> None:
    """Verify get-task requires localhost even with valid CN.

    Expected: 403 Forbidden (localhost check fails first)

    Steps:
    1. Start AR with configured relays
    2. Send get-task from non-localhost IP with correct CN
    3. Verify request is rejected (localhost validation fails first)
    """
    relay_id = str(uuid.uuid4())
    site.set_scenario([relay_id])

    serial_folder = create_config_folder(site_context.omd_root, [relay_id])
    agent_receiver.set_serial(serial_folder.serial)

    with agent_receiver.with_client_ip("192.168.1.100"):
        response = agent_receiver.get_task(
            relay_id=relay_id,
            task_id=str(uuid.uuid4()),
            site_cn=site_name,
        )

    assert response.status_code == HTTPStatus.FORBIDDEN, response.text
    assert "Request must originate from localhost" in response.text
