#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

from typing import final

import httpx
from fastapi.testclient import TestClient

from cmk.agent_receiver.lib.certs import serialize_to_pem
from cmk.agent_receiver.lib.mtls_auth_validator import INJECTED_UUID_HEADER
from cmk.agent_receiver.relay.lib.shared_types import RelayID
from cmk.relay_protocols.monitoring_data import MonitoringData
from cmk.relay_protocols.relays import RelayRegistrationResponse
from cmk.relay_protocols.tasks import HEADERS, TaskCreateRequest, TaskCreateRequestSpec

from .certs import generate_csr_pair
from .relay import random_relay_id
from .site_mock import User


@final
class AgentReceiverClient:
    """A wrapper class that gives more human readable api for writing tests

    It gives still direct access to the APIs and generally returns the raw api responses
    """

    def __init__(
        self, client: TestClient, site_name: str, user: User, serial: str | None = None
    ) -> None:
        self.client = client
        self.site_name = site_name
        self.client.headers["Authorization"] = user.bearer
        if serial:
            self.client.headers[HEADERS.SERIAL] = serial

    def set_serial(self, serial: str | None) -> None:
        if serial:
            self.client.headers[HEADERS.SERIAL] = serial
        else:
            try:
                del self.client.headers[HEADERS.SERIAL]
            except KeyError:
                pass

    def register_relay(self, relay_id: str, name: str) -> httpx.Response:
        csr_pair = generate_csr_pair(cn=relay_id)
        return self.client.post(
            f"/{self.site_name}/relays/",
            json={
                "relay_id": relay_id,
                "alias": name,
                "csr": serialize_to_pem(csr_pair[1]),
            },
        )

    def push_task(self, *, relay_id: str, spec: TaskCreateRequestSpec) -> httpx.Response:
        return self.client.post(
            f"/{self.site_name}/relays/{relay_id}/tasks",
            json=TaskCreateRequest(
                spec=spec,
            ).model_dump(),
        )

    def get_relay_tasks(self, relay_id: str, status: str | None = None) -> httpx.Response:
        params: dict[str, str] = {}
        if status:
            params = {"status": status}
        return self.client.get(
            f"/{self.site_name}/relays/{relay_id}/tasks",
            headers={INJECTED_UUID_HEADER: relay_id},
            params=params,
        )

    def update_task(
        self, *, relay_id: str, task_id: str, result_type: str, result_payload: str
    ) -> httpx.Response:
        return self.client.patch(
            f"/{self.site_name}/relays/{relay_id}/tasks/{task_id}",
            headers={INJECTED_UUID_HEADER: relay_id},
            json={
                "result_type": result_type,
                "result_payload": result_payload,
            },
        )

    def activate_config(self) -> httpx.Response:
        return self.client.post(f"/{self.site_name}/relays/activate-config")

    def forward_monitoring_data(
        self, *, relay_id: str, monitoring_data: MonitoringData
    ) -> httpx.Response:
        return self.client.post(
            f"/{self.site_name}/relays/{relay_id}/monitoring",
            headers={INJECTED_UUID_HEADER: relay_id},
            json=monitoring_data.model_dump(mode="json"),
        )


def register_relay(ar: AgentReceiverClient, name: str, relay_id: RelayID | None) -> str:
    relay_id = relay_id or random_relay_id()
    resp = ar.register_relay(relay_id=relay_id, name=name)
    parsed = RelayRegistrationResponse.model_validate_json(resp.text)
    return parsed.relay_id
