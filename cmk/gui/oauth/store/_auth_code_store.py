#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import timedelta

from pydantic import BaseModel
from redis import Redis

from cmk.utils.redis import get_redis_client

AUTH_CODE_TTL = timedelta(minutes=10)

_NAMESPACE = "mcp_auth_codes"


class AuthCodeRecord(BaseModel):
    """Everything an issued authorization code is bound to.

    user_id is the server-side session user that approved the request, never
    a client-supplied value. code_challenge is the RFC 7636 S256 challenge
    the token endpoint later verifies the client's code_verifier against.
    """

    user_id: str
    client_id: str
    redirect_uri: str
    scope: str | None
    resource: str | None
    code_challenge: str


class AuthCodeStore:
    """Redis-backed store for issued OAuth authorization codes.

    Records live under mcp_auth_codes:<code> for 10 minutes (the maximum
    authorization code lifetime RFC 6749 section 4.1.2 recommends); codes
    not redeemed in time simply expire. consume() removes the record in the
    same atomic command (GETDEL) so a code can only ever be redeemed once,
    even by concurrent requests racing for it.
    """

    def __init__(self, client: Redis | None = None) -> None:
        self._client = client if client is not None else get_redis_client()

    def store(self, code: str, record: AuthCodeRecord) -> None:
        self._client.set(f"{_NAMESPACE}:{code}", record.model_dump_json(), ex=AUTH_CODE_TTL)

    def consume(self, code: str) -> AuthCodeRecord | None:
        value = self._client.getdel(f"{_NAMESPACE}:{code}")
        if value is None:
            return None
        return AuthCodeRecord.model_validate_json(value)
