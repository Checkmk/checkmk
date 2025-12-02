#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Final, NewType

from dateutil.relativedelta import relativedelta
from pydantic import BaseModel, Field, RootModel

from cmk.ccc.store import RealIo
from cmk.ccc.user import UserId
from cmk.gui.exceptions import TokenType
from cmk.gui.type_defs import AnnotatedUserId
from cmk.utils import paths


class InvalidToken(ValueError):
    """Raised if we cannot properly parse something"""


class TokenTypeError(ValueError):
    """Token is expried or revoked but has valid type"""

    token_type: TokenType

    def __init__(self, *args: object, token_type: TokenType) -> None:
        super().__init__(*args)
        self.token_type = token_type


class TokenExpired(TokenTypeError):
    """Token is expired"""


class TokenRevoked(TokenTypeError):
    """Token was revoked"""


class DashboardToken(BaseModel):
    owner: AnnotatedUserId
    dashboard_name: str
    type_: TokenType = "dashboard"
    comment: str = ""
    disabled: bool = False


TokenId = NewType("TokenId", str)


class AuthToken(BaseModel):
    """The general token

    details/scope is stored in details.

    last_successful_verification: is meant to indicate if a token is actively used. Since we do some
        ajax calls there can be multiple requests in a short time frame. Therefore we only update after
        some time (5m) has passed.
    """

    issuer: AnnotatedUserId
    issued_at: datetime
    valid_until: datetime | None
    details: DashboardToken = Field(discriminator="type_")
    token_id: TokenId
    revoked: bool = False
    last_successful_verification: datetime | None = None


class _SerializedTokens(RootModel[dict[TokenId, AuthToken]]):
    root: dict[TokenId, AuthToken] = Field(default_factory=dict)

    def revoke(self, token_id: TokenId) -> None:
        self.root[token_id].revoked = True

    def add(self, token: AuthToken) -> None:
        self.root[token.token_id] = token

    def get(self, token_id: TokenId) -> AuthToken | None:
        return self.root.get(token_id)

    def delete(self, token_id: TokenId) -> None:
        del self.root[token_id]

    def update_last_successful_verification(self, token_id: TokenId, now: datetime) -> None:
        self.root[token_id].last_successful_verification = now


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

        if token.valid_until is not None and token.valid_until < now:
            raise TokenExpired(
                f"Token {token.token_id} expired at {token.valid_until.isoformat()}",
                token_type=token.details.type_,
            )

        if token.revoked:
            raise TokenRevoked(
                f"Token {token_id} was revoked",
                token_type=token.details.type_,
            )

        if (
            token.last_successful_verification is None
            or now - token.last_successful_verification < timedelta(minutes=5)
        ):
            with self.read_locked() as data:
                data.update_last_successful_verification(token.token_id, now)

        return token

    def revoke(self, token_id: TokenId) -> None:
        with self.read_locked() as data:
            data.revoke(token_id)

    def delete(self, token_id: TokenId) -> None:
        with self.read_locked() as data:
            data.delete(token_id)

    def issue(
        self,
        token_details: DashboardToken,
        issuer: UserId,
        now: datetime,
        valid_for: relativedelta | None = None,
    ) -> AuthToken:
        token = AuthToken(
            issuer=issuer,
            issued_at=now,
            valid_until=None if valid_for is None else now + valid_for,
            details=token_details,
            token_id=TokenId(str(uuid.uuid4())),
            revoked=False,
        )
        with self.read_locked() as data:
            data.add(token)
        return token


def get_token_store() -> TokenStore:
    return TokenStore(paths.var_dir / "token.store")
