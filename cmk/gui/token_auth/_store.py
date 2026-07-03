#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Annotated, Final, Literal, NewType

from dateutil.relativedelta import relativedelta
from pydantic import BaseModel, Discriminator, Field, PlainValidator, RootModel, WithJsonSchema

from cmk.ccc.hostaddress import HostName
from cmk.ccc.store import RealIo
from cmk.ccc.user import UserId
from cmk.gui.type_defs import AnnotatedUserId
from cmk.utils import paths
from cmk.utils.agent_registration import HostAgentConnectionMode

# NOTE: must be kept in sync with the `type_` fields in the token models below
TokenType = Literal["dashboard", "agent_registration", "agent_download", "relay_registration"]


class InvalidToken(ValueError):
    """Raised if we cannot properly parse something"""


class TokenTypeError(ValueError):
    """Token is expired or revoked but has valid type"""

    token_type: TokenType

    def __init__(self, *args: object, token_type: TokenType) -> None:
        super().__init__(*args)
        self.token_type = token_type


class TokenExpired(TokenTypeError):
    """Token is expired"""


class TokenRevoked(TokenTypeError):
    """Token was revoked"""


class TokenUseAlreadyConsumed(TokenTypeError):
    """The requested one-time use of the token was already consumed"""


class DashboardToken(BaseModel):
    type_: Literal["dashboard"] = "dashboard"
    owner: AnnotatedUserId
    dashboard_name: str
    comment: str = ""
    disabled: bool = False
    # widget_id (for linked view widget) -> view owner id
    view_owners: dict[str, AnnotatedUserId] = Field(default_factory=dict)
    synced_at: datetime  # last time the token was modified/synced with the dashboard config


AgentRegistrationUse = Literal["host_registration", "updater_registration"]

# After one of the two uses of an agent registration token is consumed, the token
# stays valid only this long, so the second registration can follow up shortly.
AGENT_REGISTRATION_TOKEN_GRACE_PERIOD: Final = timedelta(minutes=10)


class AgentRegistrationToken(BaseModel):
    type_: Literal["agent_registration"] = "agent_registration"
    host_name: Annotated[
        HostName,
        PlainValidator(HostName),
        WithJsonSchema({"type": "string"}, mode="serialization"),
    ]
    connection_mode: HostAgentConnectionMode = HostAgentConnectionMode.PULL
    comment: str = ""
    host_registration_completed_at: datetime | None = None
    updater_registration_completed_at: datetime | None = None


class RelayRegistrationToken(BaseModel):
    type_: Literal["relay_registration"] = "relay_registration"


class AgentDownloadToken(BaseModel):
    type_: Literal["agent_download"] = "agent_download"


TokenId = NewType("TokenId", str)

type TokenDetails = Annotated[
    DashboardToken | AgentRegistrationToken | AgentDownloadToken | RelayRegistrationToken,
    Discriminator("type_"),
]


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
    details: TokenDetails
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

    def consume_agent_registration_use(
        self, token_id: TokenId, use: AgentRegistrationUse, now: datetime
    ) -> None:
        """Consume one of the two one-time uses of an agent registration token

        The two uses (host registration and agent updater registration) are independent
        and can be consumed in any order. After the first use is consumed, the token
        stays valid only for a grace period so the second registration can follow up.
        Once both uses are consumed, the token is revoked.

        Raises InvalidToken, TokenTypeError or TokenUseAlreadyConsumed; in that case
        nothing is persisted.
        """
        with self.read_locked() as data:
            if (token := data.get(token_id)) is None:
                raise InvalidToken(f"Could not find token {token_id!r}")
            details = token.details
            if not isinstance(details, AgentRegistrationToken):
                raise TokenTypeError(
                    f"Token {token_id} is not an agent registration token",
                    token_type=details.type_,
                )
            match use:
                case "host_registration":
                    if details.host_registration_completed_at is not None:
                        raise TokenUseAlreadyConsumed(
                            f"Token {token_id} was already used for host registration",
                            token_type=details.type_,
                        )
                    details.host_registration_completed_at = now
                case "updater_registration":
                    if details.updater_registration_completed_at is not None:
                        raise TokenUseAlreadyConsumed(
                            f"Token {token_id} was already used for agent updater registration",
                            token_type=details.type_,
                        )
                    details.updater_registration_completed_at = now
            if (
                details.host_registration_completed_at is not None
                and details.updater_registration_completed_at is not None
            ):
                token.revoked = True
            else:
                grace_end = now + AGENT_REGISTRATION_TOKEN_GRACE_PERIOD
                if token.valid_until is None or token.valid_until > grace_end:
                    token.valid_until = grace_end

    def delete(self, token_id: TokenId) -> None:
        with self.read_locked() as data:
            data.delete(token_id)

    def issue(
        self,
        token_details: TokenDetails,
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
