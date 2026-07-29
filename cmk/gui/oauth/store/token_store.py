#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import hashlib
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, UTC

from cmk.ccc.user import UserId
from cmk.gui.oauth.store.backend import Backend


@dataclass(frozen=True, slots=True)
class TokenRecord:
    user_id: UserId
    issued_at: datetime
    expires_at: datetime
    resource: str | None
    scope: str | None

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


class TokenStore(Backend):
    def issue_token(
        self,
        user_id: UserId,
        *,
        expires_at: datetime,
        resource: str | None,
        scope: str | None,
    ) -> str:
        if not user_id:
            raise ValueError("user_id must not be empty")

        issued_at_timestamp = int(_utc_now().timestamp())
        expires_at_timestamp = _to_timestamp(expires_at)

        if expires_at_timestamp <= issued_at_timestamp:
            raise ValueError("expires_at must be later than the issue time")

        token = _mint_token()
        self._connection.execute(
            """
            INSERT INTO tokens (user_id, token_hash, issued_at, expires_at, resource, scope)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                _token_hash(token),
                issued_at_timestamp,
                expires_at_timestamp,
                resource,
                scope,
            ),
        )
        return token

    def get_by_token(self, token: str) -> TokenRecord | None:
        try:
            token_hash = _token_hash(token)
        except ValueError:
            return None

        row = self._connection.execute(
            """
            SELECT user_id, issued_at, expires_at, resource, scope
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
            SELECT user_id, issued_at, expires_at, resource, scope
            FROM tokens
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchall()
        return [_row_to_record(row) for row in rows]


def _row_to_record(row: sqlite3.Row) -> TokenRecord:
    return TokenRecord(
        user_id=UserId(row["user_id"]),
        issued_at=datetime.fromtimestamp(row["issued_at"], tz=UTC),
        expires_at=datetime.fromtimestamp(row["expires_at"], tz=UTC),
        resource=row["resource"],
        scope=row["scope"],
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
