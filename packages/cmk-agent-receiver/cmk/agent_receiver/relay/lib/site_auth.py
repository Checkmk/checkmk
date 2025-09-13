#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Generator
from typing import final, override

import httpx
from pydantic import SecretStr

from cmk.agent_receiver.utils import internal_credentials


@final
class InternalAuth(httpx.Auth):
    # TODO: async friendly
    # TODO: cache internal token
    @override
    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        creds = internal_credentials()
        request.headers["Authorization"] = f"InternalToken {creds}"
        yield request


@final
class UserAuth(httpx.Auth):
    def __init__(self, secret: SecretStr) -> None:
        self.secret = secret

    @override
    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        request.headers["Authorization"] = self.secret.get_secret_value()
        yield request


SiteAuth = InternalAuth | UserAuth
