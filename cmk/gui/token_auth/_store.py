#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import assert_never, Final, Literal, NewType

from dateutil.relativedelta import relativedelta
from pydantic import BaseModel, Field, RootModel

from cmk.ccc.store import RealIo
from cmk.ccc.user import UserId
from cmk.gui.type_defs import AnnotatedUserId


class InvalidToken(ValueError):
    """Raised if we cannot properly parse something"""


class TokenExpired(ValueError):
    """Token is expired"""


class TokenRevoked(ValueError):
    """Token was revoked"""


class DashboardToken(BaseModel):
    owner: AnnotatedUserId
    dashboard_name: str
    type_: Literal["dashboard"] = "dashboard"


TokenId = NewType("TokenId", str)


class AuthToken(BaseModel):
    issuer: AnnotatedUserId
    valid_until: datetime
    details: DashboardToken = Field(discriminator="type_")
    token_id: TokenId
    revoked: bool = False


class _SerializedTokens(RootModel[dict[TokenId, AuthToken]]):
    root: dict[TokenId, AuthToken] = Field(default_factory=dict)

    def revoke(self, token_id: TokenId) -> None:
        self.root[token_id].revoked = True

    def add(self, token: AuthToken) -> None:
        self.root[token.token_id] = token

    def get(self, token_id: TokenId) -> AuthToken | None:
        return self.root.get(token_id)


class TokenStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._io: Final = RealIo(path)

    @contextmanager
    def _locked(self) -> Iterator[None]:
        yield from self._io.locked()

    @contextmanager
    def read_locked(self) -> Iterator[_SerializedTokens]:
        with self._locked():
            data = self._read()
            yield data
            self._io.write(data.model_dump_json().encode())

    def _read(self) -> _SerializedTokens:
        return (
            _SerializedTokens.model_validate_json(raw.decode())
            if (raw := self._io.read())
            else _SerializedTokens()
        )

    def verify(self, user_provided_token: str, now: datetime) -> AuthToken:
        try:
            version, token_id = user_provided_token.split(":")
        except ValueError as e:
            raise InvalidToken("Could not parse token") from e

        if version != "0":
            raise InvalidToken(f"Invalid token version {version!r}")

        if (token := self._read().get(TokenId(token_id))) is None:
            raise InvalidToken(f"Could not find token {token_id!r}")

        if token.valid_until < now:
            raise TokenExpired(f"Token {token.token_id} expired at {token.valid_until.isoformat()}")

        if token.revoked:
            raise TokenRevoked(f"Token {token_id} was revoked")

        return token

    def revoke(self, token_id: TokenId) -> None:
        with self.read_locked() as data:
            data.revoke(token_id)

    def issue(
        self,
        token_details: DashboardToken,
        issuer: UserId,
        now: datetime,
        valid_for: relativedelta | None = None,
    ) -> AuthToken:
        if valid_for is None:
            match token_details:
                case DashboardToken():
                    valid_for = relativedelta(years=1)
                case _:
                    assert_never(token_details)

        token = AuthToken(
            issuer=issuer,
            valid_until=now + valid_for,
            details=token_details,
            token_id=TokenId(str(uuid.uuid4())),
            revoked=False,
        )
        with self.read_locked() as data:
            data.add(token)
        return token
