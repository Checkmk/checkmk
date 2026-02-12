#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from starlette.routing import Mount

from cmk.agent_receiver.lib.mtls_auth_validator import (
    INJECTED_UUID_HEADER,
    mtls_authorization_dependency,
)
from cmk.agent_receiver.main import main_app


def test_uuid_validation_route() -> None:
    app = FastAPI()
    uuid_validation_router = APIRouter(dependencies=[mtls_authorization_dependency("uuid", 400)])
    foo_validation_router = APIRouter(dependencies=[mtls_authorization_dependency("foo", 400)])

    @uuid_validation_router.get("/endpoint/{uuid}")
    def endpoint() -> dict[str, str]:
        return {"Hello": "World"}

    @foo_validation_router.get("/other/{foo}/bar")
    def bar() -> dict[str, str]:
        return {"Hello": "World"}

    app.include_router(uuid_validation_router)
    app.include_router(foo_validation_router)
    client = TestClient(app)

    response = client.get(
        "/endpoint/1234",
        headers={INJECTED_UUID_HEADER: "1234"},
    )
    assert response.status_code == 200
    assert response.json() == {"Hello": "World"}

    response = client.get(
        "/endpoint/1234",
        headers={INJECTED_UUID_HEADER: "5678"},
    )
    assert response.status_code == 400
    assert response.json() == {
        "detail": "Verified client UUID (5678) does not match UUID in URL (1234)"
    }

    response = client.get(
        "/other/1234/bar",
        headers={INJECTED_UUID_HEADER: "1234"},
    )
    assert response.status_code == 200
    assert response.json() == {"Hello": "World"}

    response = client.get(
        "/other/1234/bar",
        headers={INJECTED_UUID_HEADER: "5678"},
    )
    assert response.status_code == 400
    assert response.json() == {
        "detail": "Verified client UUID (5678) does not match UUID in URL (1234)"
    }


def test_main_app_structure() -> None:
    main_app_ = main_app()

    assert len(main_app_.routes) == 2

    assert isinstance(mount := main_app_.routes[0], Mount)
    assert mount.path == "/NO_SITE/relays"

    assert isinstance(mount := main_app_.routes[1], Mount)
    assert mount.path == "/NO_SITE/agent-receiver"
