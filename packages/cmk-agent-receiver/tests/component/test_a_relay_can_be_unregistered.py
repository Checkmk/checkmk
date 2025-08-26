#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import uuid

from fastapi.testclient import TestClient

from .test_lib.relays import register_relay, unregister_relay


def test_a_relay_can_be_unregistered(
    site_name: str, agent_receiver_test_client: TestClient
) -> None:
    """
    Test CT-2. Description:

    POST /relays/{relay_id_A}
    POST /relays/{relay_id_B}
    DELETE /relays/{relay_id_A}
    GET /relays/{relay_id_B}/tasks
    GET /relays/{relay_id_A}/tasks ⇾ 404
    Wait expiration time
    Check that cleaning expired tasks does not trigger any error regarding missing relay
    """

    relay_id_A = str(uuid.uuid4())
    register_relay(relay_id_A, site_name, agent_receiver_test_client)

    relay_id_B = str(uuid.uuid4())
    register_relay(relay_id_B, site_name, agent_receiver_test_client)

    unregister_relay(relay_id_A, site_name, agent_receiver_test_client)

    # Verify relay B have tasks queue
    response_B_tasks = agent_receiver_test_client.get(
        f"/{site_name}/agent-receiver/relays/{relay_id_B}/tasks"
    )
    assert response_B_tasks.status_code == 200, (
        f"Failed to get tasks for relay B: {response_B_tasks.text}"
    )

    response_A_tasks = agent_receiver_test_client.get(
        f"/{site_name}/agent-receiver/relays/{relay_id_A}/tasks"
    )
    assert response_A_tasks.status_code == 404, (
        f"Failed, getting tasks for relay A was not expected: {response_A_tasks.text}"
    )
    assert "Relay not found" in response_A_tasks.text, (
        f"Expected 'Relay not found' in response: {response_A_tasks.text}"
    )
