#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Unit tests for the security-headers ASGI middleware.

The daemon serves only JSON/SSE behind the site proxy, so every response must
carry the hardening headers (nosniff, frame/referrer policy, and the strict
CSP). These are pinned here so a future refactor cannot silently drop one.
"""

from __future__ import annotations

import asyncio

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient
from starlette.types import Receive, Scope, Send

from cmk.maps.backend.core.middleware import _CONTENT_SECURITY_POLICY, SecurityHeadersMiddleware


@pytest.fixture(name="client")
def _client() -> TestClient:
    async def _ok(_request: Request) -> JSONResponse:
        return JSONResponse({"ok": True})

    app = SecurityHeadersMiddleware(Starlette(routes=[Route("/x", _ok)]))
    return TestClient(app)


def test_all_security_headers_present(client: TestClient) -> None:
    resp = client.get("/x")
    assert resp.status_code == 200
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "SAMEORIGIN"
    # no-referrer so the signed ticket in ``?token=`` never leaks via Referer.
    assert resp.headers["referrer-policy"] == "no-referrer"
    assert resp.headers["x-xss-protection"] == "1; mode=block"


def test_content_security_policy_is_locked_down(client: TestClient) -> None:
    csp = client.get("/x").headers["content-security-policy"]
    assert csp == _CONTENT_SECURITY_POLICY.decode()
    # A script-free, sandboxed policy: no default-src, no script execution.
    assert "default-src 'none'" in csp
    assert "sandbox" in csp
    assert "script-src" not in csp


def test_headers_do_not_clobber_response_body(client: TestClient) -> None:
    assert client.get("/x").json() == {"ok": True}


def test_non_http_scope_passes_through_untouched() -> None:
    seen: dict[str, object] = {}

    async def _inner(scope: Scope, _receive: Receive, send: Send) -> None:
        seen["scope_type"] = scope["type"]
        seen["send"] = send

    middleware = SecurityHeadersMiddleware(_inner)

    async def _receive() -> dict[str, object]:
        return {"type": "lifespan.startup"}

    async def _send(_message: object) -> None:
        return None

    asyncio.run(middleware({"type": "lifespan"}, _receive, _send))

    # Lifespan/WebSocket scopes must reach the inner app with the ORIGINAL send
    # (the header-wrapping send is only installed for http responses).
    assert seen["scope_type"] == "lifespan"
    assert seen["send"] is _send
