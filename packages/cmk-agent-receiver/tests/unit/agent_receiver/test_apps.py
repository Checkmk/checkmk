#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from starlette.routing import Mount

from cmk.agent_receiver.lib.config import get_config
from cmk.agent_receiver.lib.mtls_auth_validator import (
    ExpectedCA,
    INJECTED_ISSUER_HEADER,
    INJECTED_UUID_HEADER,
    mtls_authorization_dependency,
)
from cmk.agent_receiver.main import main_app
from cmk.testlib.agent_receiver.certs import agent_ca_common_name


def test_uuid_validation_route() -> None:
    app = FastAPI()
    uuid_validation_router = APIRouter(
        dependencies=[mtls_authorization_dependency("uuid", 400, ExpectedCA.AGENT)]
    )
    foo_validation_router = APIRouter(
        dependencies=[mtls_authorization_dependency("foo", 400, ExpectedCA.AGENT)]
    )

    @uuid_validation_router.get("/endpoint/{uuid}")
    def endpoint() -> dict[str, str]:
        return {"Hello": "World"}

    @foo_validation_router.get("/other/{foo}/bar")
    def bar() -> dict[str, str]:
        return {"Hello": "World"}

    app.include_router(uuid_validation_router)
    app.include_router(foo_validation_router)
    client = TestClient(app)

    issuer_cn = agent_ca_common_name(get_config().site_name)

    response = client.get(
        "/endpoint/1234",
        headers={INJECTED_UUID_HEADER: "1234", INJECTED_ISSUER_HEADER: issuer_cn},
    )
    assert response.status_code == 200
    assert response.json() == {"Hello": "World"}

    response = client.get(
        "/endpoint/1234",
        headers={INJECTED_UUID_HEADER: "5678", INJECTED_ISSUER_HEADER: issuer_cn},
    )
    assert response.status_code == 400
    assert response.json() == {
        "detail": "Verified client UUID (5678) does not match UUID in URL (1234)"
    }

    response = client.get(
        "/other/1234/bar",
        headers={INJECTED_UUID_HEADER: "1234", INJECTED_ISSUER_HEADER: issuer_cn},
    )
    assert response.status_code == 200
    assert response.json() == {"Hello": "World"}

    response = client.get(
        "/other/1234/bar",
        headers={INJECTED_UUID_HEADER: "5678", INJECTED_ISSUER_HEADER: issuer_cn},
    )
    assert response.status_code == 400
    assert response.json() == {
        "detail": "Verified client UUID (5678) does not match UUID in URL (1234)"
    }


def test_uuid_validation_route_rejects_wrong_issuer() -> None:
    """A certificate whose issuer isn't the expected CA is rejected, even with a matching UUID.

    This is the CA-confusion check: mtls_authorization_dependency must not authorize a
    request based on the subject CN alone.
    """
    app = FastAPI()
    uuid_validation_router = APIRouter(
        dependencies=[mtls_authorization_dependency("uuid", 400, ExpectedCA.AGENT)]
    )

    @uuid_validation_router.get("/endpoint/{uuid}")
    def endpoint() -> dict[str, str]:
        return {"Hello": "World"}

    app.include_router(uuid_validation_router)
    client = TestClient(app)

    response = client.get(
        "/endpoint/1234",
        headers={INJECTED_UUID_HEADER: "1234", INJECTED_ISSUER_HEADER: "some other CA"},
    )
    assert response.status_code == 400
    assert "not issued by the expected CA" in response.json()["detail"]


def test_main_app_structure() -> None:
    main_app_ = main_app()

    assert len(main_app_.routes) == 2

    assert isinstance(mount := main_app_.routes[0], Mount)
    assert mount.path == "/NO_SITE/relays"

    assert isinstance(mount := main_app_.routes[1], Mount)
    assert mount.path == "/NO_SITE/agent-receiver"
