#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""ASGI middlewares that don't belong in any single router.

Kept as bare ASGI classes (not Starlette ``BaseHTTPMiddleware``) so header
inspection can short-circuit without materialising a Request object.
"""

from __future__ import annotations

from starlette.types import ASGIApp, Message, Receive, Scope, Send

# The daemon serves only JSON and SSE — never script-bearing HTML (the SPA is
# served by the GUI, uploaded assets by Apache). A maximally restrictive CSP is
# therefore safe everywhere.
_CONTENT_SECURITY_POLICY = (
    b"default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'; sandbox"
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
                headers = list(message.get("headers", []))
                headers += [
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"SAMEORIGIN"),
                    # no-referrer (not strict-origin-when-cross-origin) so the
                    # signed ticket carried in ``?token=`` on SSE / <img> URLs
                    # never leaks via the Referer header to same-origin assets.
                    (b"referrer-policy", b"no-referrer"),
                    (b"x-xss-protection", b"1; mode=block"),
                    (b"content-security-policy", _CONTENT_SECURITY_POLICY),
                ]
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_headers)
