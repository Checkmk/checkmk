#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import http
from typing import Any

import jwt
import pytest
from fastapi.testclient import TestClient

# check if we can import this or abort. Do a separate import later for mypy
pytest.importorskip("tests.testlib.openid_oauth_provider")
import tests.testlib.openid_oauth_provider as app


def config_override() -> app.Config:
    return app.Config(base_url="http://localhost:6666")


@pytest.fixture(name="client")
def _client() -> TestClient:
    app.application.dependency_overrides[app.read_config] = config_override
    return TestClient(app.application)


def test_healthz(client: TestClient) -> None:
    # when
    response = client.get("/healthz")

    # then
    assert response.status_code == http.HTTPStatus.OK
    assert response.text == '"I\'m alive"'


def test_well_known(client: TestClient) -> None:
    response = client.get("/.well-known/openid-configuration")
    assert response.status_code == 200
    expected = {
        "authorization_endpoint": "http://localhost:6666/authorize",
        "token_endpoint": "http://localhost:6666/token",
        "jwks_uri": "http://localhost:6666/.well-known/jwks.json",
        "grant_types_supported": ["authorization_code"],
        "id_token_signing_alg_values_supported": ["RS256"],
        "issuer": "checkmk",
        "response_types_supported": ["code", "token"],
        "scopes_supported": ["openid", "email"],
        "subject_types_supported": ["public"],
        "token_endpoint_auth_methods_supported": ["client_secret_post"],
    }

    assert response.json() == expected


@pytest.fixture(name="jwks_client")
def _jwks_client(client: TestClient) -> jwt.PyJWKClient:
    jwks_client = jwt.PyJWKClient("I'll mock the fetch_data")

    def fetch_data() -> Any:
        resp = client.get("/.well-known/jwks.json")
        return resp.json()

    jwks_client.fetch_data = fetch_data  # type: ignore[method-assign]
    return jwks_client


def test_jwks_json(client: TestClient, jwks_client: jwt.PyJWKClient) -> None:
    response = client.get("/.well-known/jwks.json")
    assert response.status_code == 200
    jwk = jwks_client.get_signing_key(app.KEY.kid)
    assert jwk is not None
    algo_obj = jwt.api_jws.get_algorithm_by_name("RS256")
    read_key = algo_obj.prepare_key(jwk.key)
    assert read_key.public_numbers().n == app.KEY.public.public_numbers().n


def test_token(client: TestClient, jwks_client: jwt.PyJWKClient) -> None:
    audience = "this-test-app"
    data = {"client_id": audience}
    response = client.post("/token", data=data)
    response.raise_for_status()
    id_token = response.json()["id_token"]
    signing_key = jwks_client.get_signing_key_from_jwt(id_token)
    payload = jwt.decode(id_token, signing_key.key, algorithms=["RS256"], audience=audience)
    assert "email" in payload


def test_authorize(client: TestClient) -> None:
    state = "sometext"
    redirect_uri = "http://localhost/checkmk"
    resp = client.get("/authorize", params={"state": state, "redirect_uri": redirect_uri})
    assert len(resp.history) > 0
    assert str(resp.url).startswith(redirect_uri)
    assert f"state={state}" in str(resp.url)
    assert "code=" in str(resp.url)
    assert "&code" in str(resp.url) or "&state" in str(resp.url)
