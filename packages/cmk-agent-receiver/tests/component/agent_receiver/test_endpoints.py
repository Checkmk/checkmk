#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from http import HTTPMethod, HTTPStatus
from uuid import UUID, uuid4

import httpx2
import pytest
from fastapi.testclient import TestClient

from cmk.agent_receiver.lib.mtls_auth_validator import (
    INJECTED_ISSUER_HEADER,
    INJECTED_SERIAL_HEADER,
    INJECTED_UUID_HEADER,
)
from cmk.testlib.agent_receiver.builder import AgentReceiverSite
from cmk.testlib.agent_receiver.certs import agent_ca_common_name, UNREVOKED_SERIAL_NUMBER
from cmk.testlib.agent_receiver.wiremock import (
    FoundRequests,
    Request,
    Response,
    Wiremock,
    WMapping,
)

HOST_NAME = "my-host"

STATUS_REQUEST: dict[str, object] = {
    "platform": "linux_deb",
    "installed_aghash": "fedcba9876543210",
}

NO_AGENT: dict[str, object] = {}

ROUTING_404 = {
    "title": "Not Found",
    "status": 404,
    "detail": (
        "404 Not Found: The requested URL was not found on the server. If you entered the URL "
        "manually please check your spelling and try again."
    ),
}


def _json_answer(
    status: HTTPStatus, body: object, content_type: str = "application/json"
) -> Response:
    return Response(status=status, body=json.dumps(body), headers={"Content-Type": content_type})


def _site_path(site: AgentReceiverSite, action: str) -> str:
    return (
        f"/{site.config.site_name}/check_mk/api/internal"
        f"/objects/agent_deployment_internal/{HOST_NAME}/actions/{action}/invoke"
    )


def _site_answers(
    wiremock: Wiremock, site: AgentReceiverSite, action: str, answer: Response
) -> None:
    wiremock.setup_mapping(
        WMapping(request=Request(method="POST", url=_site_path(site, action)), response=answer)
    )


def _forwarded(wiremock: Wiremock, site: AgentReceiverSite, action: str) -> list[FoundRequests]:
    return wiremock.get_all_url_path_requests(_site_path(site, action), HTTPMethod.POST)


def _request_status(
    client: TestClient, site: AgentReceiverSite, uuid: UUID, body: dict[str, object]
) -> httpx2.Response:
    return client.post(
        f"/{site.config.site_name}/agent-receiver/agent_update/status/{uuid}",
        headers={
            INJECTED_UUID_HEADER: str(uuid),
            INJECTED_ISSUER_HEADER: agent_ca_common_name(site.config.site_name),
            INJECTED_SERIAL_HEADER: UNREVOKED_SERIAL_NUMBER,
        },
        json=body,
    )


@pytest.fixture
def registered_uuid(ar_site: AgentReceiverSite) -> UUID:
    uuid = uuid4()
    agent_output_dir = ar_site.config.agent_output_dir
    agent_output_dir.mkdir(parents=True)
    (agent_output_dir / str(uuid)).symlink_to(agent_output_dir / HOST_NAME)
    return uuid


def test_status_answers_with_the_target_agent_of_the_site(
    test_client: TestClient,
    wiremock: Wiremock,
    ar_site: AgentReceiverSite,
    registered_uuid: UUID,
) -> None:
    answer = {
        "target_agent": {
            "aghash": "0123456789abcdef",
            "signatures": [{"certificate": "<PEM>", "signature": "c2lnbmF0dXJl"}],
        }
    }
    _site_answers(wiremock, ar_site, "status", _json_answer(HTTPStatus.OK, answer))

    response = _request_status(test_client, ar_site, registered_uuid, STATUS_REQUEST)

    assert response.status_code == HTTPStatus.OK
    assert response.json() == answer


def test_status_answers_that_no_agent_is_available(
    test_client: TestClient,
    wiremock: Wiremock,
    ar_site: AgentReceiverSite,
    registered_uuid: UUID,
) -> None:
    _site_answers(wiremock, ar_site, "status", _json_answer(HTTPStatus.OK, NO_AGENT))

    response = _request_status(test_client, ar_site, registered_uuid, STATUS_REQUEST)

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {}


def test_status_forwards_the_request_on_behalf_of_the_registered_host(
    test_client: TestClient,
    wiremock: Wiremock,
    ar_site: AgentReceiverSite,
    registered_uuid: UUID,
) -> None:
    report = STATUS_REQUEST | {
        "last_error": "Connection refused",
        "legacy_registration": {"host_name": HOST_NAME, "host_secret": "xR3uVq9LcK2mWn7Z"},
    }
    _site_answers(wiremock, ar_site, "status", _json_answer(HTTPStatus.OK, NO_AGENT))

    _request_status(test_client, ar_site, registered_uuid, report)

    forwarded = _forwarded(wiremock, ar_site, "status")
    assert [(r.headers["Authorization"], json.loads(r.body)) for r in forwarded] == [
        (
            f"InternalToken {ar_site.internal_credentials}",
            report | {"uuid": str(registered_uuid)},
        )
    ]


def test_status_leaves_unreported_fields_out(
    test_client: TestClient,
    wiremock: Wiremock,
    ar_site: AgentReceiverSite,
    registered_uuid: UUID,
) -> None:
    _site_answers(wiremock, ar_site, "status", _json_answer(HTTPStatus.OK, NO_AGENT))

    _request_status(
        test_client,
        ar_site,
        registered_uuid,
        STATUS_REQUEST | {"last_error": None, "legacy_registration": None},
    )

    forwarded = _forwarded(wiremock, ar_site, "status")
    assert [json.loads(r.body) for r in forwarded] == [
        STATUS_REQUEST | {"uuid": str(registered_uuid)}
    ]


@pytest.mark.parametrize(
    "body_of_the_404",
    [
        pytest.param(json.dumps(ROUTING_404), id="rest-api"),
        pytest.param("Not Found", id="plain-text"),
    ],
)
def test_status_reports_a_site_without_agent_updates_as_not_implemented(
    test_client: TestClient,
    wiremock: Wiremock,
    ar_site: AgentReceiverSite,
    registered_uuid: UUID,
    body_of_the_404: str,
) -> None:
    _site_answers(
        wiremock, ar_site, "status", Response(status=HTTPStatus.NOT_FOUND, body=body_of_the_404)
    )

    response = _request_status(test_client, ar_site, registered_uuid, STATUS_REQUEST)

    assert response.status_code == HTTPStatus.NOT_IMPLEMENTED
    assert response.json() == {"detail": "This site offers no agent updates."}
    assert len(_forwarded(wiremock, ar_site, "status")) == 1


def test_status_passes_a_refusal_of_the_site_through(
    test_client: TestClient,
    wiremock: Wiremock,
    ar_site: AgentReceiverSite,
    registered_uuid: UUID,
) -> None:
    refusal = {
        "title": "Not available on a remote site",
        "status": 501,
        "detail": "Agent deployment is only available on the central site.",
    }
    _site_answers(
        wiremock,
        ar_site,
        "status",
        _json_answer(HTTPStatus.NOT_IMPLEMENTED, refusal, "application/problem+json"),
    )

    response = _request_status(test_client, ar_site, registered_uuid, STATUS_REQUEST)

    assert response.status_code == HTTPStatus.NOT_IMPLEMENTED
    assert response.json() == {
        "detail": "Not available on a remote site - Details: "
        "Agent deployment is only available on the central site."
    }
