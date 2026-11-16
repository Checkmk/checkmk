#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
from http import HTTPStatus
from pathlib import Path

import httpx2
import pytest
from pydantic import SecretStr

from cmk.agent_receiver.lib.config import Config
from cmk.agent_receiver.relay.lib.site_auth import (
    InternalAuth,
    parse_authorization,
    SecretAuth,
    UnsupportedAuthFormatError,
)


def test_secret_auth_flow_sets_authorization_header() -> None:
    secret = SecretStr("Bearer test-token")
    auth = SecretAuth(secret)
    request = httpx2.Request("GET", "https://example.com")

    # Execute auth flow
    flow = auth.auth_flow(request)
    modified_request = next(flow)

    assert modified_request.headers["Authorization"] == "Bearer test-token"


@pytest.mark.usefixtures("site_context")
def test_auth_flow_sets_internal_token_header() -> None:
    flow = InternalAuth().sync_auth_flow(httpx2.Request("GET", "https://example.com"))

    # "lol" encoded in base64 is "bG9s"
    assert next(flow).headers["Authorization"] == "InternalToken bG9s"


@pytest.mark.parametrize("status", [HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN])
def test_retry_uses_a_rotated_secret(
    status: HTTPStatus, site_context: Config, tmp_path: Path
) -> None:
    old_secret_path = tmp_path / "old_secret"
    new_secret_path = tmp_path / "new_secret"
    old_secret_path.write_bytes(b"old-token")
    new_secret_path.write_bytes(b"new-token")
    site_context.internal_secret_path.unlink()
    site_context.internal_secret_path.symlink_to(old_secret_path)

    flow = InternalAuth().sync_auth_flow(httpx2.Request("GET", "https://example.com"))
    old_token = base64.b64encode(b"old-token").decode("ascii")
    assert next(flow).headers["Authorization"] == f"InternalToken {old_token}"

    site_context.internal_secret_path.unlink()
    site_context.internal_secret_path.symlink_to(new_secret_path)
    retry_request = flow.send(httpx2.Response(status))

    new_token = base64.b64encode(b"new-token").decode("ascii")
    assert retry_request.headers["Authorization"] == f"InternalToken {new_token}"


@pytest.mark.usefixtures("site_context")
def test_no_retry_on_success() -> None:
    auth = InternalAuth()
    request = httpx2.Request("GET", "https://example.com")

    flow = auth.sync_auth_flow(request)
    next(flow)

    # Simulate successful response
    mock_response = httpx2.Response(HTTPStatus.OK)

    with pytest.raises(StopIteration):
        flow.send(mock_response)


def test_parse_authorization_bearer() -> None:
    secret = SecretStr("Bearer testuser testpassword")
    auth = parse_authorization(secret)
    assert isinstance(auth, SecretAuth)
    assert auth.secret.get_secret_value() == "Bearer testuser testpassword"


def test_parse_authorization_cmk_token() -> None:
    secret = SecretStr("CMK-TOKEN 0:550e8400-e29b-41d4-a716-446655440000")
    auth = parse_authorization(secret)
    assert isinstance(auth, SecretAuth)
    assert auth.secret.get_secret_value() == "CMK-TOKEN 0:550e8400-e29b-41d4-a716-446655440000"


def test_parse_authorization_rejects_unknown_format() -> None:
    secret = SecretStr("Basic dXNlcjpwYXNz")
    with pytest.raises(UnsupportedAuthFormatError):
        parse_authorization(secret)
