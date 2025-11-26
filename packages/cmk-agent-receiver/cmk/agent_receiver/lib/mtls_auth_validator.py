#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated, Final

from fastapi import Header, HTTPException, Path
from fastapi.params import Depends
from starlette.status import HTTP_400_BAD_REQUEST

INJECTED_UUID_HEADER: Final[str] = "verified-uuid"


def mtls_authorization_dependency(path_alias: str) -> Depends:
    """FastAPI dependency generator for mutual TLS (mTLS) authorization.

    This function validates that the client certificate common name (CN) matches the
    UUID provided in the request URL path. It relies on a custom Uvicorn worker
    (ClientCertWorker) that intercepts incoming HTTP requests and injects the verified
    client certificate CN as a custom HTTP header.

    How it works:
    1. The ClientCertWorker uses a custom H11Protocol (_ClientCertProtocol) that
       extracts the CN from the client's SSL certificate during TLS handshake
    2. The CN is injected into the request headers using INJECTED_UUID_HEADER
       ("verified-uuid") before the request reaches FastAPI
    3. This dependency function extracts both the injected header and the UUID
       from the URL path
    4. If they don't match, the request is rejected with HTTP 400

    This approach ensures:
    - The certificate validation happens at the protocol level before FastAPI processing
    - The CN cannot be spoofed by clients (it's extracted from the verified TLS connection)
    - Individual endpoints or routers can opt-in to mTLS authorization by adding
      this dependency

    Raises:
        HTTPException: HTTP 400 if the certificate CN doesn't match the URL UUID

    Example:
        @router.post("/{uuid}/data", dependencies=[mtls_authorization_dependency("uuid")])
        async def receive_data(uuid: str): ...
    """

    def _mtls_authorization_check(
        header_uuid: Annotated[str, Header(alias=INJECTED_UUID_HEADER)],
        path_uuid: Annotated[str, Path(alias=path_alias)],
    ) -> None:
        if header_uuid != path_uuid:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"Verified client UUID ({header_uuid}) does not match UUID in URL ({path_uuid})",
            )

    return Depends(_mtls_authorization_check)
