#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from agent_receiver.certificates import CertValidationRoute
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient


def test_cert_validation_route() -> None:
    app = FastAPI()
    cert_validation_router = APIRouter(route_class=CertValidationRoute)

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
