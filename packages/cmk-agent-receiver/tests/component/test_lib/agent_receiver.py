#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import final

import httpx
from fastapi.testclient import TestClient

from cmk.relay_protocols.tasks import TaskType


@final
class AgentReceiverClient:
    """A wrapper class that gives more human readable api for writing tests

    It gives still direct access to the APIs and generally returns the raw api responses

    """

    def __init__(self, client: TestClient, site_name: str) -> None:
        self.client = client
        self.site_name = site_name

    def register_relay(self, relay_id: str) -> httpx.Response:
        return self.client.post(
            f"/{self.site_name}/agent-receiver/relays",
            json={
                "relay_id": relay_id,
                "relay_name": "Relay A",  # TODO: Remove still unused create relay fields
                "csr": "CSR for Relay A",
                "auth_token": "auth-token-A",
            },
        )

    def unregister_relay(self, relay_id: str) -> httpx.Response:
        return self.client.delete(f"/{self.site_name}/agent-receiver/relays/{relay_id}")

    def push_task(
        self,
        relay_id: str,
        task_type: TaskType,
        task_payload: str,
    ) -> httpx.Response:
        return self.client.post(
            f"/{self.site_name}/agent-receiver/relays/{relay_id}/tasks",
            json={
                "type": task_type,
                "payload": task_payload,
            },
        )

    def get_all_relay_tasks(self, relay_id: str) -> httpx.Response:
        return self.client.get(f"/{self.site_name}/agent-receiver/relays/{relay_id}/tasks")
