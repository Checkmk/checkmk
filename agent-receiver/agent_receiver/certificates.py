#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Callable, Coroutine

from cryptography.x509 import load_pem_x509_csr
from cryptography.x509.oid import NameOID
from fastapi import Request, Response
from fastapi.routing import APIRoute


def uuid_from_pem_csr(pem_csr: str) -> str:
    try:
        return (
            load_pem_x509_csr(pem_csr.encode())
            .subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0]
            .value
        )
    except ValueError:
        return "[CSR parsing failed]"


class CertValidationRoute(APIRoute):
    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            response: Response = await original_route_handler(request)
            return response

        return custom_route_handler
