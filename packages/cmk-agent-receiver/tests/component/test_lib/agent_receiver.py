#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

from typing import final

import httpx
from fastapi.testclient import TestClient

from cmk.relay_protocols.tasks import Task, TaskCreateRequest

from .site_mock import User


@final
class AgentReceiverClient:
    """A wrapper class that gives more human readable api for writing tests

    It gives still direct access to the APIs and generally returns the raw api responses
    """

    def __init__(self, client: TestClient, site_name: str, user: User) -> None:
        self.client = client
        self.site_name = site_name
        self.user = user

    def register_relay(self, name: str) -> httpx.Response:
        return self.client.post(
            f"/{self.site_name}/agent-receiver/relays",
            json={
                "relay_name": name,
                "csr": "CSR for Relay A",
            },
            headers={"Authorization": self.user.bearer},
        )

    def unregister_relay(self, relay_id: str) -> httpx.Response:
        return self.client.delete(
            f"/{self.site_name}/agent-receiver/relays/{relay_id}",
            headers={"Authorization": self.user.bearer},
        )

    def push_task(self, *, relay_id: str, task: Task) -> httpx.Response:
        return self.client.post(
            f"/{self.site_name}/agent-receiver/relays/{relay_id}/tasks",
            json=TaskCreateRequest(
                task=task,
            ).model_dump(),
            headers={"Authorization": self.user.bearer},
        )

    def get_relay_tasks(self, relay_id: str, status: str | None = None) -> httpx.Response:
        params: dict[str, str] = {}
        if status:
            params = {"status": status}
        return self.client.get(
            f"/{self.site_name}/agent-receiver/relays/{relay_id}/tasks",
            params=params,
            headers={"Authorization": self.user.bearer},
        )

    def update_task(
        self, *, relay_id: str, task_id: str, result_type: str, result_payload: str
    ) -> httpx.Response:
        return self.client.patch(
            f"/{self.site_name}/agent-receiver/relays/{relay_id}/tasks/{task_id}",
            json={
                "result_type": result_type,
                "result_payload": result_payload,
            },
            headers={"Authorization": self.user.bearer},
        )
