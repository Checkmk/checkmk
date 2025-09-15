#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import AsyncGenerator, Generator
from typing import final, override

import httpx
from pydantic import SecretStr

from cmk.agent_receiver.utils import (
    async_internal_credentials,
    internal_credentials,
)


@final
class InternalAuth(httpx.Auth):
    def __init__(self) -> None:
        self._cached_token: str | None = None

    def _get_auth_header_sync(self) -> str:
        if self._cached_token is None:
            self._cached_token = f"InternalToken {internal_credentials()}"
        return self._cached_token

    async def _get_auth_header_async(self) -> str:
        if self._cached_token is None:
            token = await async_internal_credentials()
            self._cached_token = f"InternalToken {token}"
        return self._cached_token

    def _invalidate_cache(self) -> None:
        self._cached_token = None

    @override
    def sync_auth_flow(
        self, request: httpx.Request
    ) -> Generator[httpx.Request, httpx.Response, None]:
        request.headers["Authorization"] = self._get_auth_header_sync()
        response = yield request

        # Handle credential rotation on unauthorized responses
        if response.status_code in (401, 403):
            self._invalidate_cache()
            request.headers["Authorization"] = self._get_auth_header_sync()
            yield request

    @override
    async def async_auth_flow(
        self, request: httpx.Request
    ) -> AsyncGenerator[httpx.Request, httpx.Response]:
        request.headers["Authorization"] = await self._get_auth_header_async()
        response = yield request

        # Handle credential rotation on unauthorized responses
        if response.status_code in (401, 403):
            self._invalidate_cache()
            request.headers["Authorization"] = await self._get_auth_header_async()
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
