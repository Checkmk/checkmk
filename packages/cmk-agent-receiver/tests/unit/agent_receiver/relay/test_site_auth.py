#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
from http import HTTPStatus
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr

from cmk.agent_receiver.config import Config
from cmk.agent_receiver.relay.lib.site_auth import InternalAuth, UserAuth


def test_user_auth_flow_sets_authorization_header() -> None:
    secret = SecretStr("Bearer test-token")
    auth = UserAuth(secret)
    request = httpx.Request("GET", "https://example.com")

    # Execute auth flow
    flow = auth.auth_flow(request)
    modified_request = next(flow)

    assert modified_request.headers["Authorization"] == "Bearer test-token"


@pytest.mark.usefixtures("site_context")
def test_sync_auth_flow_sets_internal_token_header() -> None:
    auth = InternalAuth()
    request = httpx.Request("GET", "https://example.com")

    # Execute auth flow
    flow = auth.sync_auth_flow(request)
    modified_request = next(flow)

    # "lol" encoded in base64 is "bG9s"
    expected_token = base64.b64encode(b"lol").decode("ascii")
    assert modified_request.headers["Authorization"] == f"InternalToken {expected_token}"


@pytest.mark.asyncio
@pytest.mark.usefixtures("site_context")
async def test_async_auth_flow_sets_internal_token_header() -> None:
    auth = InternalAuth()
    request = httpx.Request("GET", "https://example.com")

    # Execute auth flow
    flow = auth.async_auth_flow(request)
    modified_request = await anext(flow)

    # "lol" encoded in base64 is "bG9s"
    expected_token = base64.b64encode(b"lol").decode("ascii")
    assert modified_request.headers["Authorization"] == f"InternalToken {expected_token}"


def test_sync_credential_rotation_on_401(site_context: Config, tmp_path: Path) -> None:
    # Set up two different secret files
    old_secret_path = tmp_path / "old_secret"
    new_secret_path = tmp_path / "new_secret"
    old_secret_path.write_bytes(b"old-token")
    new_secret_path.write_bytes(b"new-token")

    # Start with old secret
    site_context.internal_secret_path.unlink()
    site_context.internal_secret_path.symlink_to(old_secret_path)

    auth = InternalAuth()
    request = httpx.Request("GET", "https://example.com")

    # Execute auth flow
    flow = auth.sync_auth_flow(request)
    modified_request = next(flow)
    old_token = base64.b64encode(b"old-token").decode("ascii")
    assert modified_request.headers["Authorization"] == f"InternalToken {old_token}"

    # Simulate credential rotation by changing the file
    site_context.internal_secret_path.unlink()
    site_context.internal_secret_path.symlink_to(new_secret_path)

    # Simulate 401 response to trigger credential refresh
    mock_response = httpx.Response(HTTPStatus.UNAUTHORIZED)
    retry_request = flow.send(mock_response)

    new_token = base64.b64encode(b"new-token").decode("ascii")
    assert retry_request.headers["Authorization"] == f"InternalToken {new_token}"


@pytest.mark.asyncio
async def test_async_credential_rotation_on_401(site_context: Config, tmp_path: Path) -> None:
    # Set up two different secret files
    old_secret_path = tmp_path / "old_secret"
    new_secret_path = tmp_path / "new_secret"
    old_secret_path.write_bytes(b"old-token")
    new_secret_path.write_bytes(b"new-token")

    # Start with old secret
    site_context.internal_secret_path.unlink()
    site_context.internal_secret_path.symlink_to(old_secret_path)

    auth = InternalAuth()
    request = httpx.Request("GET", "https://example.com")

    # Execute auth flow
    flow = auth.async_auth_flow(request)
    modified_request = await anext(flow)
    old_token = base64.b64encode(b"old-token").decode("ascii")
    assert modified_request.headers["Authorization"] == f"InternalToken {old_token}"

    # Simulate credential rotation by changing the file
    site_context.internal_secret_path.unlink()
    site_context.internal_secret_path.symlink_to(new_secret_path)

    # Simulate 401 response to trigger credential refresh
    mock_response = httpx.Response(HTTPStatus.UNAUTHORIZED)
    retry_request = await flow.asend(mock_response)

    new_token = base64.b64encode(b"new-token").decode("ascii")
    assert retry_request.headers["Authorization"] == f"InternalToken {new_token}"


def test_sync_credential_rotation_on_403(site_context: Config, tmp_path: Path) -> None:
    # Set up two different secret files
    old_secret_path = tmp_path / "old_secret"
    new_secret_path = tmp_path / "new_secret"
    old_secret_path.write_bytes(b"old-token")
    new_secret_path.write_bytes(b"new-token")

    # Start with old secret
    site_context.internal_secret_path.unlink()
    site_context.internal_secret_path.symlink_to(old_secret_path)

    auth = InternalAuth()
    request = httpx.Request("GET", "https://example.com")

    flow = auth.sync_auth_flow(request)
    modified_request = next(flow)
    old_token = base64.b64encode(b"old-token").decode("ascii")
    assert modified_request.headers["Authorization"] == f"InternalToken {old_token}"

    # Simulate credential rotation by changing the file
    site_context.internal_secret_path.unlink()
    site_context.internal_secret_path.symlink_to(new_secret_path)

    # Simulate 403 response to trigger credential refresh
    mock_response = httpx.Response(HTTPStatus.FORBIDDEN)
    retry_request = flow.send(mock_response)

    new_token = base64.b64encode(b"new-token").decode("ascii")
    assert retry_request.headers["Authorization"] == f"InternalToken {new_token}"


@pytest.mark.usefixtures("site_context")
def test_no_retry_on_success() -> None:
    auth = InternalAuth()
    request = httpx.Request("GET", "https://example.com")

    flow = auth.sync_auth_flow(request)
    next(flow)

    # Simulate successful response
    mock_response = httpx.Response(HTTPStatus.OK)

    with pytest.raises(StopIteration):
        flow.send(mock_response)
