#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Unit tests for the daemon's ASGI middlewares.

The daemon serves only JSON/SSE behind the site proxy, so every response must
carry the hardening headers (nosniff, frame/referrer policy, and the strict
CSP). These are pinned here so a future refactor cannot silently drop one.
Request bodies are bounded before the session check, because the proxied path
has no Apache body limit. A request the browser marks as sent by another site
is refused before it reaches a route. The event stream is gzip-compressed with
every event flushed on its own, so compression never holds an event back.
"""

import asyncio
import random
import zlib
from http import HTTPStatus

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse
from starlette.routing import Route
from starlette.testclient import TestClient
from starlette.types import Message, Receive, Scope, Send

from cmk.fastapi import FastAPI
from cmk.maps.backend.app import create_app, MAX_REQUEST_BODY_BYTES
from cmk.maps.backend.core.middleware import _CONTENT_SECURITY_POLICY, SecurityHeadersMiddleware

_JSON = {"Content-Type": "application/json"}


@pytest.fixture(name="client")
def _client() -> TestClient:
    async def _ok(_request: Request) -> JSONResponse:
        return JSONResponse({"ok": True})

    app = SecurityHeadersMiddleware(Starlette(routes=[Route("/x", _ok)]))
    return TestClient(app)


def test_all_security_headers_present(client: TestClient) -> None:
    resp = client.get("/x")
    assert resp.status_code == HTTPStatus.OK
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "SAMEORIGIN"
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


def test_oversized_body_is_refused_before_authentication() -> None:
    client = TestClient(create_app())

    resp = client.post(
        "/api/v1/maps/m/register",
        content=b"x" * (MAX_REQUEST_BODY_BYTES + 1),
        headers=_JSON,
    )

    assert resp.status_code == HTTPStatus.REQUEST_ENTITY_TOO_LARGE


def test_chunked_oversized_body_is_refused() -> None:
    client = TestClient(create_app())
    chunk = b"x" * (MAX_REQUEST_BODY_BYTES // 2 + 1)

    resp = client.post("/api/v1/maps/m/register", content=iter([chunk, chunk]), headers=_JSON)

    assert "content-length" not in resp.request.headers
    assert resp.status_code == HTTPStatus.REQUEST_ENTITY_TOO_LARGE


def test_a_request_from_another_site_is_refused_before_authentication() -> None:
    client = TestClient(create_app())

    resp = client.post(
        "/api/v1/maps/m/register",
        json={"config": {"name": "m"}},
        headers={"Sec-Fetch-Site": "cross-site"},
    )

    assert resp.status_code == HTTPStatus.FORBIDDEN


def test_the_health_check_answers_another_site() -> None:
    client = TestClient(create_app())

    resp = client.get("/api/health", headers={"Sec-Fetch-Site": "cross-site"})

    assert resp.status_code == HTTPStatus.OK


_EVENTS = [b'event: state_update\ndata: {"n": 1}\n\n', b'event: state_update\ndata: {"n": 2}\n\n']


def _app_with_event_stream() -> FastAPI:
    async def _events(_request: Request) -> StreamingResponse:
        return StreamingResponse(iter(_EVENTS), media_type="text/event-stream")

    app = create_app()
    app.add_route("/events", _events)
    return app


@pytest.mark.parametrize(
    "accept_encoding, content_encoding", [("gzip", "gzip"), ("identity", None)]
)
def test_event_stream_is_compressed_only_for_a_client_that_takes_gzip(
    accept_encoding: str, content_encoding: str | None
) -> None:
    resp = TestClient(_app_with_event_stream()).get(
        "/events", headers={"accept-encoding": accept_encoding}
    )

    assert resp.headers.get("content-encoding") == content_encoding
    assert resp.content == b"".join(_EVENTS)


def _gzipped_bodies(app: FastAPI, path: str) -> list[bytes]:
    """The response's body chunks as sent, after checking they are gzipped."""
    sent: list[Message] = []

    async def _receive() -> Message:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def _send(message: Message) -> None:
        sent.append(message)

    scope: Scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.4"},
        "method": "GET",
        "path": path,
        "query_string": b"",
        "headers": [(b"accept-encoding", b"gzip")],
    }
    asyncio.run(app(scope, _receive, _send))
    start = next(m for m in sent if m["type"] == "http.response.start")
    assert (b"content-encoding", b"gzip") in start["headers"]
    return [m["body"] for m in sent if m["type"] == "http.response.body"]


def test_each_event_can_be_read_as_soon_as_it_is_sent() -> None:
    bodies = _gzipped_bodies(_app_with_event_stream(), "/events")
    decompressor = zlib.decompressobj(zlib.MAX_WBITS | 16)

    assert [decompressor.decompress(body) for body in bodies[: len(_EVENTS)]] == _EVENTS


def test_compression_looks_back_no_further_than_its_small_window() -> None:
    # Within reach of a 16 KiB window, out of reach of the 8 KiB one.
    block = random.Random(0).randbytes(9 * 1024)

    async def _repeated(_request: Request) -> Response:
        return Response(block * 2, media_type="application/octet-stream")

    app = create_app()
    app.add_route("/repeated", _repeated)

    body = b"".join(_gzipped_bodies(app, "/repeated"))

    assert zlib.decompress(body, zlib.MAX_WBITS | 16) == block * 2
    assert len(body) > len(block) * 2
