#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, final

import httpx
from fastapi.testclient import TestClient

from cmk.agent_receiver.lib.certs import serialize_to_pem
from cmk.agent_receiver.lib.mtls_auth_validator import INJECTED_UUID_HEADER
from cmk.agent_receiver.relay.lib.shared_types import RelayID, Serial
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
        self, client: TestClient, site_name: str, user: User, serial: Serial | None = None
    ) -> None:
        self.client = client
        self.site_name = site_name
        self.client.headers["Authorization"] = user.bearer
        self.set_serial(serial)
        self._client_ip_override: tuple[str, int] | None = None

    @contextmanager
    def with_client_ip(self, client_ip: str = "127.0.0.1", client_port: int = 0) -> Iterator[None]:
        """Context manager to temporarily set the client IP for requests.

        This is useful for testing endpoints that have IP-based access control,
        such as localhost_only_dependency which requires requests from 127.0.0.1.

        Args:
            client_ip: The IP address to set as the request origin (default: "127.0.0.1")
            client_port: The port to set as the request origin (default: 0)

        Example:
            with agent_receiver.with_client_ip("127.0.0.1"):
                response = agent_receiver.push_task(relay_id=relay_id, spec=spec)
        """
        # TestClient uses a _TestClientTransport from starlette
        # We need to wrap the transport's app
        original_transport = self.client._transport  # noqa: SLF001
        original_app = original_transport.app  # type: ignore[attr-defined]
        client_tuple = (client_ip, client_port)

        # Create wrapper that injects client IP into scope
        async def client_ip_wrapper(scope: Any, receive: Any, send: Any) -> None:
            # https://asgi.readthedocs.io/en/latest/specs/main.html#connection-scope
            # https://asgi.readthedocs.io/en/latest/specs/www.html#http-connection-scope
            if scope["type"] == "http":
                scope["client"] = client_tuple
            await original_app(scope, receive, send)

        # Replace the app in the transport
        original_transport.app = client_ip_wrapper  # type: ignore[attr-defined]
        try:
            yield
        finally:
            # Restore original app
            original_transport.app = original_app  # type: ignore[attr-defined]

    def set_serial(self, serial: Serial | None) -> None:
        if serial:
            self.client.headers[HEADERS.SERIAL] = str(serial)
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

    def refresh_cert(self, relay_id: str) -> httpx.Response:
        """Refresh the certificate for a relay.

        This endpoint allows a relay to request a new certificate by submitting
        a new Certificate Signing Request (CSR). The relay must be authenticated
        via mTLS using its current certificate.

        Args:
            relay_id: The UUID of the relay requesting certificate refresh

        Returns:
            httpx.Response containing RelayRefreshCertResponse with:
                - root_cert: The root CA certificate in PEM format
                - client_cert: The newly signed client certificate in PEM format

        Note:
            - The relay must authenticate using mTLS with its existing certificate
            - The CSR's Common Name must match the relay_id
        """
        csr_pair = generate_csr_pair(cn=relay_id)
        return self.client.post(
            f"/{self.site_name}/relays/{relay_id}/csr",
            headers={INJECTED_UUID_HEADER: relay_id},
            json={
                "csr": serialize_to_pem(csr_pair[1]),
            },
        )

    def get_relay_status(
        self, relay_id: str, injected_uuid_header_value: str | None = None
    ) -> httpx.Response:
        """Get relay status.

        This endpoint returns the relay state by comparing local config and CMK API.
        The relay must be authenticated via mTLS using its certificate.

        Args:
            relay_id: The UUID of the relay to get status for
            injected_uuid_header_value: if None, will use the relay_id valus as header
                otherwise use the custom value

        Returns:
            httpx.Response containing RelayStatusResponse with:
                - relay_id: The relay's unique identifier
                - state: The relay's state (CONFIGURED, PENDING_ACTIVATION, PENDING_DELETION)

        Status codes:
            - 200: Success
            - 404: Relay not found in CMK configuration nor local config
            - 502: CMK API error
        """
        return self.client.get(
            f"/{self.site_name}/relays/{relay_id}/status",
            headers={INJECTED_UUID_HEADER: injected_uuid_header_value or relay_id},
        )

    def push_task(
        self, *, relay_id: str, spec: TaskCreateRequestSpec, site_cn: str
    ) -> httpx.Response:
        headers = {
            INJECTED_UUID_HEADER: site_cn,
        }
        return self.client.post(
            f"/{self.site_name}/relays/{relay_id}/tasks",
            headers=headers,
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

    def activate_config(self, site_cn: str) -> httpx.Response:
        headers = {
            INJECTED_UUID_HEADER: site_cn,
        }
        return self.client.post(
            f"/{self.site_name}/relays/activate-config",
            headers=headers,
        )

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
