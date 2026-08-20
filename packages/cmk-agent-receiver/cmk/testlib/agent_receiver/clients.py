#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterator
from contextlib import contextmanager
from http import HTTPStatus
from typing import final

import httpx2
from fastapi.testclient import TestClient
from starlette.types import Receive, Scope, Send

from cmk.agent_receiver.lib.certs import serialize_to_pem
from cmk.agent_receiver.lib.mtls_auth_validator import INJECTED_ISSUER_HEADER, INJECTED_UUID_HEADER
from cmk.agent_receiver.relay.lib.shared_types import RelayID, Serial, TaskID
from cmk.relay_protocols.monitoring_data import MonitoringData
from cmk.relay_protocols.tasks import (
    FetchAdHocTask,
    HEADERS,
    TaskCreateRequest,
    TaskCreateRequestSpec,
    TaskCreateResponse,
    TaskListResponse,
)

from .certs import generate_csr_pair, relay_ca_common_name
from .relay_config_generator import RelayConfig
from .site_mock import User


@final
class RelayRegistrationClient:
    """An HTTP based client for anonymous or token-authed registration of a Relay on CMK's API"""

    def __init__(self, http: TestClient, site_name: str) -> None:
        self.fastAPI_client = http
        self.site_name = site_name

    def register_with_user(self, relay_id: str, alias: str, user: User) -> httpx2.Response:
        csr_pair = generate_csr_pair(cn=relay_id)
        return self.fastAPI_client.post(
            f"/{self.site_name}/relays/",
            headers={"Authorization": user.bearer},
            json={
                "relay_id": relay_id,
                "alias": alias,
                "csr": serialize_to_pem(csr_pair[1]),
            },
        )

    def register_with_token(self, relay_id: str, alias: str, token: str) -> httpx2.Response:
        csr_pair = generate_csr_pair(cn=relay_id)
        return self.fastAPI_client.post(
            f"/{self.site_name}/relays/",
            headers={"Authorization": f"CMK-TOKEN {token}"},
            json={
                "relay_id": relay_id,
                "alias": alias,
                "csr": serialize_to_pem(csr_pair[1]),
            },
        )

    def register(self, name: str, relay_id: RelayID | str, user: User) -> None:
        resp = self.register_with_user(relay_id=RelayID(relay_id), alias=name, user=user)
        assert resp.status_code == HTTPStatus.OK, resp.text


@final
class RelayClient:
    """An HTTP based client for a registered Relay that calls the CMK's Relay API endpoints as itself."""

    def __init__(
        self,
        http: TestClient,
        site_name: str,
        relay_id: str,
        identity_cn: str | None = None,
    ) -> None:
        self.fastAPI_client = http
        self.site_name = site_name
        self.relay_id = relay_id
        self.identity_cn = identity_cn or relay_id
        self._serial: Serial | None = None
        # Relay endpoints are mTLS-authorized against this CA (see mtls_auth_validator.py).
        # Real traffic gets this injected by the ClientCertWorker from the actual
        # certificate; here we set the expected value directly since this client is
        # used against the in-process TestClient, which never presents a certificate.
        self._relay_issuer_cn = relay_ca_common_name(site_name)

    def refresh_cert(self) -> httpx2.Response:
        csr_pair = generate_csr_pair(cn=self.relay_id)
        return self.fastAPI_client.post(
            f"/{self.site_name}/relays/{self.relay_id}/csr",
            headers={
                INJECTED_UUID_HEADER: self.identity_cn,
                INJECTED_ISSUER_HEADER: self._relay_issuer_cn,
            },
            json={
                "csr": serialize_to_pem(csr_pair[1]),
            },
        )

    def get_status(self) -> httpx2.Response:
        return self.fastAPI_client.get(
            f"/{self.site_name}/relays/{self.relay_id}/status",
            headers={
                INJECTED_UUID_HEADER: self.identity_cn,
                INJECTED_ISSUER_HEADER: self._relay_issuer_cn,
            },
        )

    def get_tasks(self, status: str | None = None) -> httpx2.Response:
        headers = {
            INJECTED_UUID_HEADER: self.identity_cn,
            INJECTED_ISSUER_HEADER: self._relay_issuer_cn,
        }
        if self._serial:
            headers[HEADERS.SERIAL] = str(self._serial)
        params: dict[str, str] = {}
        if status:
            params = {"status": status}
        return self.fastAPI_client.get(
            f"/{self.site_name}/relays/{self.relay_id}/tasks",
            headers=headers,
            params=params,
        )

    def get_task_list(self, status: str | None = None) -> TaskListResponse:
        response = self.get_tasks(status=status)
        assert response.status_code == HTTPStatus.OK, response.text
        return TaskListResponse.model_validate(response.json())

    def update_task(self, task_id: str, result_type: str, result_payload: str) -> httpx2.Response:
        headers = {
            INJECTED_UUID_HEADER: self.identity_cn,
            INJECTED_ISSUER_HEADER: self._relay_issuer_cn,
        }
        if self._serial:
            headers[HEADERS.SERIAL] = str(self._serial)
        return self.fastAPI_client.patch(
            f"/{self.site_name}/relays/{self.relay_id}/tasks/{task_id}",
            headers=headers,
            json={
                "result_type": result_type,
                "result_payload": result_payload,
            },
        )

    def forward_monitoring_data(self, monitoring_data: MonitoringData) -> httpx2.Response:
        headers = {
            INJECTED_UUID_HEADER: self.identity_cn,
            INJECTED_ISSUER_HEADER: self._relay_issuer_cn,
        }
        if self._serial:
            headers[HEADERS.SERIAL] = str(self._serial)
        return self.fastAPI_client.post(
            f"/{self.site_name}/relays/{self.relay_id}/monitoring",
            headers=headers,
            json=monitoring_data.model_dump(mode="json"),
        )

    def apply_config(self, push: RelayConfig) -> None:
        """Set this client's Serial header. Per-client state; does NOT affect the shared TestClient."""
        self._serial = push.serial


@final
class SiteClient:
    """A client that wraps local-site administrative operations."""

    def __init__(
        self,
        http: TestClient,
        site_name: str,
        cn: str | None = None,
        source_ip: str = "127.0.0.1",
    ) -> None:
        self.fastAPI_client = http
        self.site_name = site_name
        self.cn = cn if cn is not None else site_name
        self.source_ip = source_ip

    def push_task(self, relay_id: str, spec: TaskCreateRequestSpec) -> httpx2.Response:
        with _with_client_ip(self.fastAPI_client, self.source_ip):
            return self.fastAPI_client.post(
                f"/{self.site_name}/relays/{relay_id}/tasks",
                headers={INJECTED_UUID_HEADER: self.cn},
                json=TaskCreateRequest(
                    spec=spec,
                ).model_dump(),
            )

    def create_task(self, relay_id: str, spec: TaskCreateRequestSpec) -> TaskCreateResponse:
        response = self.push_task(relay_id, spec)
        assert response.status_code == HTTPStatus.OK, response.text
        return TaskCreateResponse.model_validate(response.json())

    def get_task(self, relay_id: str, task_id: str) -> httpx2.Response:
        with _with_client_ip(self.fastAPI_client, self.source_ip):
            return self.fastAPI_client.get(
                f"/{self.site_name}/relays/{relay_id}/tasks/{task_id}",
                headers={INJECTED_UUID_HEADER: self.cn},
            )

    def activate_config(self) -> httpx2.Response:
        with _with_client_ip(self.fastAPI_client, self.source_ip):
            return self.fastAPI_client.post(
                f"/{self.site_name}/relays/activate-config",
                headers={INJECTED_UUID_HEADER: self.cn},
            )

    def add_tasks(self, count: int, relay_id: str) -> list[TaskID]:
        """Add FetchAdHocTasks for a relay. Returns list of task IDs."""
        return [
            TaskID(self.create_task(relay_id, FetchAdHocTask(payload=f"payload_{i}")).task_id)
            for i in range(count)
        ]


@contextmanager
def _with_client_ip(
    http: TestClient, client_ip: str = "127.0.0.1", client_port: int = 0
) -> Iterator[None]:
    """Context manager to temporarily set the client IP for requests.

    This is useful for testing endpoints that have IP-based access control,
    such as localhost_only_dependency which requires requests from 127.0.0.1.
    """
    original_transport = http._transport  # noqa: SLF001
    original_app = original_transport.app  # type: ignore[attr-defined]
    client_tuple = (client_ip, client_port)

    async def client_ip_wrapper(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            scope["client"] = client_tuple
        await original_app(scope, receive, send)

    original_transport.app = client_ip_wrapper  # type: ignore[attr-defined]
    try:
        yield
    finally:
        original_transport.app = original_app  # type: ignore[attr-defined]
