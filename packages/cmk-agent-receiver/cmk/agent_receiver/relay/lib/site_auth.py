#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Generator
from http import HTTPStatus
from typing import Final, final, override

import httpx2
from pydantic import SecretStr

from cmk.agent_receiver.lib.auth import internal_credentials

SUPPORTED_AUTH_PREFIXES: Final = ("Bearer ", "CMK-TOKEN ")


@final
class InternalAuth(httpx2.Auth):
    @override
    def auth_flow(self, request: httpx2.Request) -> Generator[httpx2.Request, httpx2.Response]:
        request.headers["Authorization"] = f"InternalToken {internal_credentials()}"
        response = yield request

        # The secret may have been regenerated while the request was on its way.
        if response.status_code in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
            request.headers["Authorization"] = f"InternalToken {internal_credentials()}"
            yield request


@final
class SecretAuth(httpx2.Auth):
    def __init__(self, secret: SecretStr) -> None:
        self.secret = secret

    @override
    def auth_flow(self, request: httpx2.Request) -> Generator[httpx2.Request, httpx2.Response]:
        request.headers["Authorization"] = self.secret.get_secret_value()
        yield request


SiteAuth = InternalAuth | SecretAuth


class UnsupportedAuthFormatError(ValueError):
    pass


def parse_authorization(secret: SecretStr) -> SecretAuth:
    value = secret.get_secret_value()
    if value.startswith(SUPPORTED_AUTH_PREFIXES):
        return SecretAuth(secret)
    raise UnsupportedAuthFormatError(value)
