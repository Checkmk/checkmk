#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from starlette.routing import Mount

from cmk.agent_receiver.apps_and_routers import _UUIDValidationRoute, AGENT_RECEIVER_APP
from cmk.agent_receiver.main import main_app


def test_uuid_validation_route() -> None:
    app = FastAPI()
    uuid_validation_router = APIRouter(route_class=_UUIDValidationRoute)

    @uuid_validation_router.get("/endpoint/1234")
    def endpoint() -> dict[str, str]:
        return {"Hello": "World"}

    app.include_router(uuid_validation_router)
    client = TestClient(app)

    response = client.get(
        "/endpoint/1234",
        headers={"verified-uuid": "1234"},
    )
    assert response.status_code == 200
    assert response.json() == {"Hello": "World"}

    response = client.get(
        "/endpoint/1234",
        headers={"verified-uuid": "5678"},
    )
    assert response.status_code == 400
    assert response.json() == {
        "detail": "Verified client UUID (5678) does not match UUID in URL (1234)"
    }


def test_main_app_structure() -> None:
    main_app_ = main_app()
    # we only want one route, namely the one to the sub-app which is mounted under the site name
    assert len(main_app_.routes) == 1
    assert isinstance(mount := main_app_.routes[0], Mount)
    assert mount.app is AGENT_RECEIVER_APP
    assert mount.path == "/NO_SITE/agent-receiver"
