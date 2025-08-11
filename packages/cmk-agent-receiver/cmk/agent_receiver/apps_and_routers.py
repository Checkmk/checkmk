#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Coroutine
from typing import Final, override

from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.status import HTTP_400_BAD_REQUEST


class _UUIDValidationRoute(APIRoute):
    @override
    def get_route_handler(self) -> Callable[[Request], Coroutine[object, object, Response]]:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            if mismatch_response := _mismatch_header_vs_url_uuid_response(request):
                return mismatch_response
            response: Response = await original_route_handler(request)
            return response

        return custom_route_handler


def _mismatch_header_vs_url_uuid_response(request: Request) -> JSONResponse | None:
    header_uuid = request.headers.get("verified-uuid", "header missing")
    url_uuid = request.url.path.split("/")[-1]
    return (
        None if header_uuid == url_uuid else _create_400_bad_request(header_uuid, url_uuid=url_uuid)
    )


def _create_400_bad_request(header_uuid: str, *, url_uuid: str) -> JSONResponse:
    return JSONResponse(
        status_code=HTTP_400_BAD_REQUEST,
        content={
            "detail": (
                f"Verified client UUID ({header_uuid}) does not match UUID in URL ({url_uuid})"
            )
        },
    )


AGENT_RECEIVER_APP: Final = FastAPI(title="Checkmk Agent Receiver")
UUID_VALIDATION_ROUTER: Final = APIRouter(route_class=_UUIDValidationRoute)
