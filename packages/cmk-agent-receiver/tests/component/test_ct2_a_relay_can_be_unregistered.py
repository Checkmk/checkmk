#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import uuid

from fastapi.testclient import TestClient


def test_ct02_a_relay_can_be_unregistered(
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

    relay_id_A = uuid.uuid4()
    relay_id_B = uuid.uuid4()

    response_A = agent_receiver_test_client.post(
        f"/{site_name}/agent-receiver/relays",
        json={
            "relay_id": str(relay_id_A),
            "relay_name": "Relay A",
            "csr": "CSR for Relay A",
            "auth_token": "auth-token-A",
        },
    )
    print(f"Response A: {response_A}")
    assert response_A.status_code == 200, f"Failed to register relay A: {response_A.text}"

    response_B = agent_receiver_test_client.post(
        f"/{site_name}/agent-receiver/relays",
        json={
            "relay_id": str(relay_id_B),
            "relay_name": "Relay B",
            "csr": "CSR for Relay B",
            "auth_token": "auth-token-B",
        },
    )
    assert response_B.status_code == 200, f"Failed to register relay B: {response_B.text}"

    # Delete relay A
    response_delete = agent_receiver_test_client.delete(
        f"/{site_name}/agent-receiver/relays/{relay_id_A}"
    )
    assert response_delete.status_code == 200, (
        f"Failed to unregister relay A: {response_delete.text}"
    )

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
