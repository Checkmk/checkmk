#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import fastapi
import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from cmk.agent_receiver.lib.mtls_auth_validator import INJECTED_UUID_HEADER
from cmk.agent_receiver.relay.api.routers.tasks.dependencies import site_cn_authorization


def test_site_cn_validation_route(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test site CN authorization dependency with matching and mismatching CNs."""
    # Mock the get_local_site_cn function to return a known site CN
    # We need to patch it in the site_cn_authorization module where it's used
    from cmk.agent_receiver.relay.api.routers.tasks.libs import site_cn_authorization as auth_lib

    monkeypatch.setattr(auth_lib, "get_local_site_cn", lambda: "test-site-cn")

    app = FastAPI()
    site_cn_router = APIRouter()

    @site_cn_router.get("/foo", dependencies=[fastapi.Depends(site_cn_authorization)])
    def foo() -> dict[str, str]:
        return {"whatever": "data"}

    app.include_router(site_cn_router)
    client = TestClient(app)

    # Test successful request with matching CN
    response = client.get(
        "/foo",
        headers={INJECTED_UUID_HEADER: "test-site-cn"},
    )
    print(response.text)  # nosemgrep: disallow-print
    assert response.status_code == 200
    assert response.json() == {"whatever": "data"}

    # Test failed request with mismatching CN
    response = client.get(
        "/foo",
        headers={INJECTED_UUID_HEADER: "wrong-site-cn"},
    )
    assert response.status_code == 403
    assert response.json() == {
        "detail": "Client certificate CN (wrong-site-cn) does not match local site CN (test-site-cn)"
    }
