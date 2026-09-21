#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.status import HTTP_403_FORBIDDEN

from cmk.agent_receiver.lib.config import get_config
from cmk.agent_receiver.lib.mtls_auth_validator import (
    ExpectedCA,
    INJECTED_ISSUER_HEADER,
    INJECTED_SERIAL_HEADER,
    INJECTED_UUID_HEADER,
    mtls_authorization_dependency,
)
from cmk.testlib.agent_receiver.certs import agent_ca_common_name, revoke_serial_number

_UUID = "ff09de6f-2c11-4d7d-9a37-09e1d02a4ce4"


def _client() -> TestClient:
    app = FastAPI()

    @app.get(
        "/{uuid}/data",
        dependencies=[mtls_authorization_dependency("uuid", HTTP_403_FORBIDDEN, ExpectedCA.AGENT)],
    )
    def data() -> dict[str, str]:
        return {"agent": "output"}

    return TestClient(app)


def _get(client: TestClient, serial_number: int) -> tuple[int, str]:
    response = client.get(
        f"/{_UUID}/data",
        headers={
            INJECTED_UUID_HEADER: _UUID,
            INJECTED_ISSUER_HEADER: agent_ca_common_name(get_config().site_name),
            INJECTED_SERIAL_HEADER: f"{serial_number:X}",
        },
    )
    return response.status_code, response.text


def test_agent_ca_revocation_rejects_only_the_revoked_certificate() -> None:
    revoked, still_valid = 0xB0A710E5, 0xC0FFEE
    revoke_serial_number(get_config().agent_ca_path, revoked)
    client = _client()

    assert _get(client, still_valid) == (200, '{"agent":"output"}')

    status_code, body = _get(client, revoked)
    assert status_code == HTTP_403_FORBIDDEN
    assert "has been revoked" in body
