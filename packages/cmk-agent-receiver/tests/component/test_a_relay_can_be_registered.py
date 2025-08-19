#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import uuid

from fastapi.testclient import TestClient


def test_a_relay_can_be_registered(site_name: str, agent_receiver_test_client: TestClient) -> None:
    """
    Test CT-1. Description:

    POST /relays/{relay_id_A}
    POST /relays/{relay_id_B}
    GET /relays/{relay_id_A}/tasks
    GET /relays/{relay_id_B}/tasks
    """

    relay_id_A = str(uuid.uuid4())
    relay_id_B = str(uuid.uuid4())

    response_A = agent_receiver_test_client.post(
        f"/{site_name}/agent-receiver/relays",
        json={
            "relay_id": relay_id_A,
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
            "relay_id": relay_id_B,
            "relay_name": "Relay B",
            "csr": "CSR for Relay B",
            "auth_token": "auth-token-B",
        },
    )
    assert response_B.status_code == 200, f"Failed to register relay B: {response_B.text}"

    # Verify both relays have tasks queue
    response_A_tasks = agent_receiver_test_client.get(
        f"/{site_name}/agent-receiver/relays/{relay_id_A}/tasks"
    )
    assert response_A_tasks.status_code == 200, (
        f"Failed to get tasks for relay A: {response_A_tasks.text}"
    )

    response_B_tasks = agent_receiver_test_client.get(
        f"/{site_name}/agent-receiver/relays/{relay_id_B}/tasks"
    )
    assert response_B_tasks.status_code == 200, (
        f"Failed to get tasks for relay B: {response_B_tasks.text}"
    )
