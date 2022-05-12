#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Callable, Coroutine, Optional

from agent_receiver.log import configure_logger
from agent_receiver.site_context import log_path, site_name
from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.status import HTTP_400_BAD_REQUEST


class _UUIDValidationRoute(APIRoute):
    @staticmethod
    def _mismatch_header_vs_url_uuid_response(request: Request) -> Optional[JSONResponse]:
        return (
            None
            if (header_uuid := request.headers["verified-uuid"])
            == (url_uuid := request.url.path.split("/")[-1])
            else JSONResponse(
                status_code=HTTP_400_BAD_REQUEST,
                content={
                    "detail": f"Verified client UUID ({header_uuid}) does not match UUID in URL ({url_uuid})"
                },
            )
        )

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            if mismatch_response := self._mismatch_header_vs_url_uuid_response(request):
                return mismatch_response
            response: Response = await original_route_handler(request)
            return response

        return custom_route_handler


agent_receiver_app = FastAPI(title="Checkmk Agent Receiver")
uuid_validation_router = APIRouter(route_class=_UUIDValidationRoute)


def main_app() -> FastAPI:
    configure_logger(log_path())

    # register endpoints
    from agent_receiver import endpoints  # pylint: disable=unused-import

    # this must happen *after* registering the endpoints
    agent_receiver_app.include_router(uuid_validation_router)

    main_app_ = FastAPI(
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
    )
    main_app_.mount(f"/{site_name()}/agent-receiver", agent_receiver_app)
    return main_app_
