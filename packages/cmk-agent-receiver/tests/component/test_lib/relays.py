#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from fastapi.testclient import TestClient


def register_relay(relay_id: str, site_name: str, agent_receiver_test_client: TestClient) -> None:
    response = agent_receiver_test_client.post(
        f"/{site_name}/agent-receiver/relays",
        json={
            "relay_id": relay_id,
            "relay_name": "Relay A",  # TODO: Remove still unused create relay fields
            "csr": "CSR for Relay A",
            "auth_token": "auth-token-A",
        },
    )
    assert response.status_code == 200, response.text


def unregister_relay(relay_id: str, site_name: str, agent_receiver_test_client: TestClient) -> None:
    response = agent_receiver_test_client.delete(f"/{site_name}/agent-receiver/relays/{relay_id}")
    assert response.status_code == 200, response.text
