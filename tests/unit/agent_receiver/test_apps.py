#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from agent_receiver.apps import _CertValidationRoute, agent_receiver_app, main_app
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from starlette.routing import Mount


def test_cert_validation_route() -> None:
    app = FastAPI()
    cert_validation_router = APIRouter(route_class=_CertValidationRoute)

    @cert_validation_router.get("/endpoint")
    def endpoint():
        return {"Hello": "World"}

    app.include_router(cert_validation_router)
    client = TestClient(app)

    response = client.get(
        "/endpoint",
    )
    assert response.status_code == 200
    assert response.json() == {"Hello": "World"}


def test_main_app_structure() -> None:
    main_app_ = main_app()
    # we only want one route, namely the one to the sub-app which is mounted under the site name
    assert len(main_app_.routes) == 1
    assert isinstance(mount := main_app_.routes[0], Mount)
    assert mount.app is agent_receiver_app
    assert mount.path == "/NO_SITE/agent-receiver"
