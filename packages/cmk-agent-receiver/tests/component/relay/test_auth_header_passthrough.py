#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from http import HTTPMethod, HTTPStatus

import pytest
from fastapi.testclient import TestClient

from cmk.agent_receiver.lib.certs import serialize_to_pem
from cmk.testlib.agent_receiver.agent_receiver import AgentReceiverClient
from cmk.testlib.agent_receiver.certs import generate_csr_pair
from cmk.testlib.agent_receiver.relay import random_relay_id
from cmk.testlib.agent_receiver.site_mock import OP, SiteMock
from cmk.testlib.agent_receiver.wiremock import Request, Response, Wiremock, WMapping


def test_bearer_auth_header_passed_to_site_api_unchanged(
    wiremock: Wiremock,
    site: SiteMock,
    agent_receiver: AgentReceiverClient,
) -> None:
    relay_id = random_relay_id()
    site.set_scenario([], [(relay_id, OP.ADD)])

    resp = agent_receiver.register_relay(relay_id, "test-relay")
    assert resp.status_code == HTTPStatus.OK

    assert _get_site_api_auth_headers(wiremock, site) == [
        agent_receiver.client.headers["Authorization"]
    ]


def test_token_auth_header_passed_to_site_api_unchanged(
    wiremock: Wiremock,
    site: SiteMock,
    agent_receiver: AgentReceiverClient,
) -> None:
    relay_id = random_relay_id()
    token = "0:550e8400-e29b-41d4-a716-446655440000"
    site.set_scenario([], [(relay_id, OP.ADD)])

    resp = agent_receiver.register_relay_with_token(relay_id, "test-relay", token=token)
    assert resp.status_code == HTTPStatus.OK

    assert _get_site_api_auth_headers(wiremock, site) == [f"CMK-TOKEN {token}"]


@pytest.mark.parametrize(
    "auth_header",
    [
        "InvalidFormat",
        "Basic dXNlcjpwYXNz",
    ],
)
def test_auth_header_rejected_for_unsupported_format(
    test_client: TestClient,
    site_name: str,
    auth_header: str,
) -> None:
    relay_id = random_relay_id()
    csr_pair = generate_csr_pair(cn=relay_id)
    resp = test_client.post(
        f"/{site_name}/relays/",
        headers={"Authorization": auth_header},
        json={"relay_id": relay_id, "alias": "test-relay", "csr": serialize_to_pem(csr_pair[1])},
    )
    assert resp.status_code == HTTPStatus.UNAUTHORIZED
    assert "Unsupported authorization format" in resp.json()["detail"]


def test_site_api_error_returned_by_ar(
    wiremock: Wiremock,
    site: SiteMock,
    test_client: TestClient,
) -> None:
    relay_id = random_relay_id()
    wiremock.setup_mapping(
        WMapping(
            request=Request(
                method="POST",
                url=f"{site.base_route}/domain-types/relay/collections/all",
            ),
            response=Response(status=HTTPStatus.UNAUTHORIZED, body="Invalid credentials"),
        )
    )
    csr_pair = generate_csr_pair(cn=relay_id)
    resp = test_client.post(
        f"/{site.site_name}/relays/",
        headers={"Authorization": "Bearer wrong_user wrong_pass"},
        json={"relay_id": relay_id, "alias": "test-relay", "csr": serialize_to_pem(csr_pair[1])},
    )
    assert resp.status_code == HTTPStatus.BAD_GATEWAY
    assert "Invalid credentials" in resp.json()["detail"]


def _get_site_api_auth_headers(wiremock: Wiremock, site: SiteMock) -> list[str]:
    requests = wiremock.get_all_url_path_requests(
        f"/{site.site_name}/check_mk/api/unstable/domain-types/relay/collections/all",
        HTTPMethod.POST,
    )
    return [r.headers["Authorization"] for r in requests]
