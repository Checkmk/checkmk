#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from fastapi.testclient import TestClient

from cmk.relay_protocols.tasks import TaskType


def push_task(
    site_name: str,
    agent_receiver_test_client: TestClient,
    relay_id: str,
    task_type: TaskType,
    task_payload: str,
) -> None:
    response = agent_receiver_test_client.post(
        f"/{site_name}/agent-receiver/relays/{relay_id}/tasks",
        json={
            "type": task_type,
            "payload": task_payload,
        },
    )
    assert response.status_code == 200, response.text
