#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from http import HTTPStatus

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

CROSS_ORIGIN_DETAIL = "cross-origin request refused"

NOT_JSON_DETAIL = "request body must be application/json"

_SEC_FETCH_SITE = b"sec-fetch-site"
_CONTENT_LENGTH = b"content-length"
_TRANSFER_ENCODING = b"transfer-encoding"
_CONTENT_TYPE = b"content-type"


class RequestShapeMiddleware:
    """Refuses a request the browser marks as sent by another site, and a body that is not
    JSON, before the app sees it.

    The browser sends the GUI session cookie with such a request too, so it would act as
    the user.
    """

    def __init__(self, app: ASGIApp, *, exempt_paths: frozenset[str] = frozenset()) -> None:
        self.app = app
        # A health check answers anyone, so it has no request to refuse
        self.exempt_paths = exempt_paths

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] in self.exempt_paths:
            await self.app(scope, receive, send)
            return

        if not _is_same_origin(scope):
            response = JSONResponse(
                {"detail": CROSS_ORIGIN_DETAIL}, status_code=HTTPStatus.FORBIDDEN
            )
        elif _has_body(scope) and not _is_json(scope):
            response = JSONResponse(
                {"detail": NOT_JSON_DETAIL}, status_code=HTTPStatus.UNSUPPORTED_MEDIA_TYPE
            )
        else:
            await self.app(scope, receive, send)
            return

        await response(scope, receive, send)


def _header_values(scope: Scope, name: bytes) -> list[bytes]:
    return [value for key, value in scope["headers"] if key == name]


def _is_same_origin(scope: Scope) -> bool:
    values = _header_values(scope, _SEC_FETCH_SITE)
    return not values or values == [b"same-origin"]


def _has_body(scope: Scope) -> bool:
    if _header_values(scope, _TRANSFER_ENCODING):
        return True
    match _header_values(scope, _CONTENT_LENGTH):
        case []:
            return False
        case [value] if value.isdigit():
            return int(value) > 0
        case _:
            return True


def _is_json(scope: Scope) -> bool:
    match _header_values(scope, _CONTENT_TYPE):
        case [value]:
            media_type = value.partition(b";")[0].strip().lower()
            return media_type == b"application/json"
        case _:
            return False
