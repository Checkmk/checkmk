#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any
from unittest.mock import Mock

import fastapi
import pytest
from fastapi import APIRouter, FastAPI, HTTPException
from starlette.datastructures import Address

from cmk.agent_receiver.relay.api.routers.tasks.libs.localhost_authorization import (
    validate_localhost_authorization,
)


def test_localhost_only_validation() -> None:
    """Test localhost-only authorization dependency with various client addresses."""
    app = FastAPI()
    router = APIRouter()

    @router.get("/test", dependencies=[fastapi.Depends(validate_localhost_authorization)])
    def test_endpoint() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(router)

    # TestClient doesn't set request.client properly by default.
    # We test the validation function directly with mock requests
    # since TestClient doesn't allow us to easily configure client addresses

    # Helper to create mock request with specific client address
    def create_mock_request(client_host: str) -> Any:
        mock_request = Mock()
        mock_request.client = Address(client_host, 12345)
        return mock_request

    # Test successful IPv4 localhost
    mock_request = create_mock_request("127.0.0.1")
    validate_localhost_authorization(mock_request)

    # Test successful IPv6 localhost
    mock_request = create_mock_request("::1")
    validate_localhost_authorization(mock_request)

    # Test failed remote IPv4
    mock_request = create_mock_request("192.168.1.100")
    with pytest.raises(HTTPException) as exc_info:
        validate_localhost_authorization(mock_request)
    assert exc_info.value.status_code == 403
    assert (
        "Access denied: Request must originate from localhost (client: 192.168.1.100)"
        in exc_info.value.detail
    )

    # Test failed remote IPv6
    mock_request = create_mock_request("2001:db8::1")
    with pytest.raises(HTTPException) as exc_info:
        validate_localhost_authorization(mock_request)
    assert exc_info.value.status_code == 403
    assert (
        "Access denied: Request must originate from localhost (client: 2001:db8::1)"
        in exc_info.value.detail
    )

    # Test with None client
    mock_request = Mock()
    mock_request.client = None
    with pytest.raises(HTTPException) as exc_info:
        validate_localhost_authorization(mock_request)
    assert exc_info.value.status_code == 403
    assert (
        "Access denied: Request must originate from localhost (client: unknown)"
        in exc_info.value.detail
    )
