#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Localhost authorization logic for validating requests originate from localhost."""

from fastapi import HTTPException
from starlette.requests import Request
from starlette.status import HTTP_403_FORBIDDEN

from cmk.agent_receiver.lib.log import logger


def validate_localhost_authorization(request: Request) -> None:
    """Validate that the incoming request originates from localhost only.

    This function performs authorization by checking that the client IP address
    matches localhost (127.0.0.1 for IPv4, ::1 for IPv6, or ::ffff:127.0.0.1 for
    IPv4-mapped IPv6 address). It's used to ensure that only local requests are accepted.

    Args:
        request: The FastAPI/Starlette request object containing client information

    Raises:
        HTTPException: HTTP 403 if the request doesn't originate from localhost
    """
    if request.client is None or request.client.host not in (
        "127.0.0.1",
        "::1",
        "::ffff:127.0.0.1",
    ):
        client_host = request.client.host if request.client else "unknown"
        logger.warning(
            f"Localhost authorization failed: Request from {client_host} attempted to access {request.url.path}"
        )
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail=f"Access denied: Request must originate from localhost (client: {client_host})",
        )
