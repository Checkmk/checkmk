# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from http import HTTPStatus
from urllib.parse import parse_qs, urlparse

import fastapi as fapi
import jwt
from cmk_dev_site.saas.config import AdminPanelUrlConfig
from cmk_dev_site.saas.constants import TENANT_ID
from cmk_dev_site.saas.oidc_service import (
    AUTHORIZATION_CODES,
    authorize,
    authorize_login,
    DEFAULT_USERNAME,
    KEY,
    tenant_role_mapping,
    token,
    TokenPayload,
)


def test_authorize_shows_plain_login_form() -> None:
    """Verify the GET /authorize endpoint returns the HTML login form."""
    response = authorize(state="abc", redirect_uri="http://example.com/callback")

    assert response.status_code == HTTPStatus.OK
    body = bytes(response.body).decode()
    assert '<form method="post" action="/authorize">' in body
    assert f'name="username" value="{DEFAULT_USERNAME}"' in body
    assert 'name="role" value="user"' in body
    assert 'name="role" value="admin" checked' in body
    assert '<button type="submit">Login</button>' in body


def test_authorize_login_redirects_with_generated_code() -> None:
    """Verify the POST /authorize endpoint generates a code and redirects."""
    AUTHORIZATION_CODES.clear()

    response = authorize_login(
        state="abc",
        redirect_uri="http://example.com/callback",
        username="alice@example.com",
        role="user",
    )

    assert response.status_code == HTTPStatus.SEE_OTHER
    location = response.headers["location"]
    parsed = urlparse(location)
    params = parse_qs(parsed.query)
    code = params["code"][0]
    assert params["state"] == ["abc"]
    assert AUTHORIZATION_CODES[code].username == "alice@example.com"
    assert AUTHORIZATION_CODES[code].user_role == "user"


def test_token_and_tenant_role_mapping_use_selected_login() -> None:
    """Verify the full flow: from code generation to tenant role verification."""
    AUTHORIZATION_CODES.clear()

    # 1. Simulate the form submission
    authorize_response = authorize_login(
        state="state-1",
        redirect_uri="http://example.com/callback",
        username="alice@example.com",
        role="user",
    )
    location = authorize_response.headers["location"]
    code = parse_qs(urlparse(location).query)["code"][0]

    # 2. Exchange the code for a token
    token_response = token(client_id="client-1", code=code)
    token_value = token_response.access_token

    # 3. Validate the JWT payload
    payload = TokenPayload.model_validate(
        jwt.decode(token_value, KEY.public, algorithms=["RS256"], options={"verify_aud": False})
    )
    assert payload.email == "alice@example.com"
    assert payload.user_role == "user"
    assert payload.tenant_id == TENANT_ID

    # 4. Verify the tenant API returns the selected role
    tenants_response = tenant_role_mapping(authorization=f"Bearer {token_value}")
    assert tenants_response.model_dump() == {"tenants": {TENANT_ID: {"user_role": "user"}}}
    assert code not in AUTHORIZATION_CODES


def test_token_rejects_unknown_authorization_code() -> None:
    """Verify that invalid codes return a 400 error."""
    AUTHORIZATION_CODES.clear()

    try:
        token(client_id="client-1", code="unknown")
    except fapi.HTTPException as exc:
        assert exc.status_code == HTTPStatus.BAD_REQUEST
        assert exc.detail == "Invalid authorization code"
    else:
        raise AssertionError("expected invalid authorization code to be rejected")


def test_admin_panel_config_contains_otel_activation_script_path() -> None:
    payload = AdminPanelUrlConfig().model_dump()

    assert payload["otel_collector_receiver_activation_script_path"] == "/usr/bin/true"
