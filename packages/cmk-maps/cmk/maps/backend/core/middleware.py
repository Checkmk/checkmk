#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""ASGI middlewares that don't belong in any single router.

Kept as bare ASGI classes (not Starlette ``BaseHTTPMiddleware``) so header
inspection can short-circuit without materialising a Request object.
"""

import zlib
from typing import Final, override

from starlette.datastructures import Headers
from starlette.middleware.gzip import GZipMiddleware, GZipResponder
from starlette.types import ASGIApp, Message, Receive, Scope, Send

# The daemon serves only JSON and SSE — never script-bearing HTML (the SPA is
# served by the GUI, uploaded assets by Apache). A maximally restrictive CSP is
# therefore safe everywhere.
_CONTENT_SECURITY_POLICY = (
    b"default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'; sandbox"
)

SECURITY_HEADERS: Final = (
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"SAMEORIGIN"),
    (b"referrer-policy", b"no-referrer"),
    (b"x-xss-protection", b"1; mode=block"),
    (b"content-security-policy", _CONTENT_SECURITY_POLICY),
)


class SecurityHeadersMiddleware:
    """Add security-related HTTP headers to every response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = [*message.get("headers", []), *SECURITY_HEADERS]
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_headers)


class _CompactGZipResponder(GZipResponder):
    @property
    @override
    def compressor(self) -> zlib._Compress:
        if self._compressor is None:
            self._compressor = zlib.compressobj(
                self.compresslevel, zlib.DEFLATED, 16 + 13, memLevel=6
            )
        return self._compressor


class CompactGZipMiddleware(GZipMiddleware):
    """``GZipMiddleware`` with a quarter of the compressor memory.

    An event stream keeps its compressor for as long as the map is open, so its
    size counts once per viewer. The JSON states compress as well with the
    smaller window.
    """

    @override
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or "gzip" not in Headers(scope=scope).get("accept-encoding", ""):
            await super().__call__(scope, receive, send)
            return
        responder = _CompactGZipResponder(
            self.app,
            self.minimum_size,
            compresslevel=self.compresslevel,
            thread_minimum_size=self.thread_minimum_size,
            exclude_content_types=self.exclude_content_types,
        )
        await responder(scope, receive, send)
