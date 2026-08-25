#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import hashlib
import secrets
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, UTC

from cmk.ccc.resulttype import Error, OK, Result
from cmk.ccc.user import UserId
from cmk.gui.log import logger
from cmk.gui.oauth.store.backend import Backend, connect, oauth_db_path
from cmk.gui.scopes import format_scopes, InvalidScopeError, parse_scopes, ScopeId


@dataclass(frozen=True, slots=True)
class TokenRecord:
    user_id: UserId
    issued_at: datetime
    expires_at: datetime
    resource: str | None
    scope: frozenset[ScopeId]
    client_id: str

    def is_valid(self, *, at: datetime | None = None) -> bool:
        current_time = at or _utc_now()
        if current_time.tzinfo is None:
            raise ValueError("datetime values must be timezone-aware")
        return current_time.astimezone(UTC) < self.expires_at


_PREFIX = "cmko1"


def _mint_token() -> str:
    return f"{_PREFIX}.{secrets.token_urlsafe(32)}"


def looks_like_token(token: str) -> bool:
    """Whether token is shaped like one this store could have issued.

    A cheap format check only - doesn't verify the token exists or is
    still valid, and needs no store connection. Lets callers (see
    cmk.gui.auth) tell an OAuth access token attempt apart from other
    Bearer credential schemes before paying for a lookup.
    """
    prefix, dot, secret = token.partition(".")
    return bool(dot and secret and prefix == f"{_PREFIX}")


@dataclass(frozen=True, slots=True)
class UnknownClient:
    """The client_id does not (or no longer) reference a registered client.

    Returned by issue_token when the foreign key on tokens.client_id rejects
    the insert -- e.g. the client was deleted between the authorization
    request and the code redemption.
    """


class TokenStore(Backend):
    def issue_token(
        self,
        user_id: UserId,
        *,
        expires_at: datetime,
        resource: str | None,
        scope: frozenset[ScopeId],
        client_id: str,
    ) -> Result[str, UnknownClient]:
        """The new access token, or UnknownClient if client_id is not a registered client.

        A client deleted between the authorization request and the code
        redemption takes its grants with it (tokens.client_id is ON DELETE
        CASCADE), so there is nothing left to issue against.
        """
        if not user_id:
            raise ValueError("user_id must not be empty")
        if not client_id:
            raise ValueError("client_id must not be empty")
        if not scope:
            raise ValueError("scope must not be empty")

        issued_at_timestamp = int(_utc_now().timestamp())
        expires_at_timestamp = _to_timestamp(expires_at)

        if expires_at_timestamp <= issued_at_timestamp:
            raise ValueError("expires_at must be later than the issue time")

        token = _mint_token()
        try:
            self._connection.execute(
                """
                INSERT INTO tokens
                    (user_id, token_hash, issued_at, expires_at, resource, scope, client_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    _token_hash(token),
                    issued_at_timestamp,
                    expires_at_timestamp,
                    resource,
                    format_scopes(scope),
                    client_id,
                ),
            )
        except sqlite3.IntegrityError:
            # The client_id foreign key is the only constraint left to trip:
            # the ValueError guards above cover every other CHECK on the
            # table, and token_hash is a fresh sha256 hexdigest.
            logger.exception(
                "Refusing to issue an OAuth access token: client %(client_id)s is not registered",
                {"client_id": client_id},
            )
            return Error(UnknownClient())
        return OK(token)

    def get_by_token(self, token: str) -> TokenRecord | None:
        try:
            token_hash = _token_hash(token)
        except ValueError:
            return None

        row = self._connection.execute(
            """
            SELECT user_id, issued_at, expires_at, resource, scope, client_id
            FROM tokens
            WHERE token_hash = ?
            """,
            (token_hash,),
        ).fetchone()

        if row is None:
            return None

        return _row_to_record(row)

    def list_by_user(self, user_id: UserId) -> list[TokenRecord]:
        rows = self._connection.execute(
            """
            SELECT user_id, issued_at, expires_at, resource, scope, client_id
            FROM tokens
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchall()
        return [record for row in rows if (record := _row_to_record(row)) is not None]


@contextmanager
def get_token_store() -> Iterator[TokenStore]:
    """Get the token store, on a connection closed at the end of the with block."""
    with connect(oauth_db_path()) as connection:
        yield TokenStore(connection)


def _row_to_record(row: sqlite3.Row) -> TokenRecord | None:
    """The row as a record, or None if its scope is not one we could have written."""
    try:
        scope = parse_scopes(row["scope"] or "")
    except InvalidScopeError:
        logger.warning(
            "Refusing OAuth access token of user %(user_id)s: stored scope %(scope)r is not usable",
            {"user_id": row["user_id"], "scope": row["scope"]},
        )
        return None

    return TokenRecord(
        user_id=UserId(row["user_id"]),
        issued_at=datetime.fromtimestamp(row["issued_at"], tz=UTC),
        expires_at=datetime.fromtimestamp(row["expires_at"], tz=UTC),
        resource=row["resource"],
        scope=scope,
        client_id=row["client_id"],
    )


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _to_timestamp(value: datetime) -> int:
    if value.tzinfo is None:
        raise ValueError("datetime values must be timezone-aware")
    return int(value.astimezone(UTC).timestamp())


def _token_hash(token: str) -> str:
    if not looks_like_token(token):
        raise ValueError("not a well-formed token")
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
