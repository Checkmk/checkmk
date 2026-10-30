#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import hashlib
import secrets
import sqlite3
from collections.abc import Collection, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, UTC

from cmk.ccc.resulttype import Error, OK, Result
from cmk.ccc.user import UserId
from cmk.gui.log import logger
from cmk.gui.oauth.token.backend import connect
from cmk.gui.scopes import format_scopes, InvalidScopeError, parse_scopes, ScopeId
from cmk.schema_manager.backend.sqlite import write_transaction


@dataclass(frozen=True, slots=True)
class TokenRecord:
    token_hash: str
    user_id: UserId
    issued_at: datetime
    expires_at: datetime
    resource: str | None
    scope: frozenset[ScopeId]
    client_id: str
    grant_id: str | None

    def is_valid(self, *, at: datetime | None = None) -> bool:
        current_time = at or _utc_now()
        if current_time.tzinfo is None:
            raise ValueError("datetime values must be timezone-aware")
        return current_time.astimezone(UTC) < self.expires_at


_ACCESS_TOKEN_PREFIX = "cmko1"
_REFRESH_TOKEN_PREFIX = "cmkr1"

# Rotated refresh tokens are kept so that a replay is recognized as reuse.
# Once expired for this long they are purged, so the table does not grow
# without bound.
_REFRESH_TOKEN_RETENTION = timedelta(days=30)


def _mint_token(prefix: str) -> str:
    return f"{prefix}.{secrets.token_urlsafe(32)}"


def looks_like_token(token: str) -> bool:
    """Whether token is shaped like one this store could have issued.

    A cheap format check only - doesn't verify the token exists or is
    still valid, and needs no store connection. Lets callers (see
    cmk.gui.auth) tell an OAuth access token attempt apart from other
    Bearer credential schemes before paying for a lookup.
    """
    return _has_prefix(token, _ACCESS_TOKEN_PREFIX)


def _has_prefix(token: str, expected_prefix: str) -> bool:
    prefix, dot, secret = token.partition(".")
    return bool(dot and secret and prefix == expected_prefix)


def _require_grant_arguments(user_id: UserId, client_id: str, scope: frozenset[ScopeId]) -> None:
    if not user_id:
        raise ValueError("user_id must not be empty")
    if not client_id:
        raise ValueError("client_id must not be empty")
    if not scope:
        raise ValueError("scope must not be empty")


@dataclass(frozen=True, slots=True)
class UnknownClient:
    """The client_id does not (or no longer) reference a registered client.

    Returned by start_grant and issue_delegated_token when the foreign key on client_id
    rejects the insert -- e.g. the client was deleted between the authorization
    request and the code redemption.
    """


@dataclass(frozen=True, slots=True)
class IssuedAccessToken:
    access: str
    expires_in: int


@dataclass(frozen=True, slots=True)
class IssuedTokens(IssuedAccessToken):
    refresh: str


@dataclass(frozen=True, slots=True)
class GrantRecord:
    grant_id: str
    user_id: UserId
    client_id: str
    resource: str | None
    scope: frozenset[ScopeId]
    created_at: datetime
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class RefreshTokenRecord:
    issued_at: datetime
    expires_at: datetime
    rotated_at: datetime | None
    grant: GrantRecord


class TokenStore:
    """Borrows `connection`; it is closed when the `with get_token_store()` block ends."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def get_by_token(self, token: str) -> TokenRecord | None:
        try:
            token_hash = _access_token_hash(token)
        except ValueError:
            return None

        row = self._connection.execute(
            """
            SELECT token_hash, user_id, issued_at, expires_at, resource, scope, client_id, grant_id
            FROM tokens
            WHERE token_hash = ?
            """,
            (token_hash,),
        ).fetchone()

        if row is None:
            return None

        return _row_to_record(row)

    def start_grant(
        self,
        user_id: UserId,
        *,
        resource: str | None,
        scope: frozenset[ScopeId],
        client_id: str,
        expires_at: datetime,
        refresh_token_expires_at: datetime,
        access_token_expires_at: datetime,
    ) -> Result[IssuedTokens, UnknownClient]:
        """A new grant with its first refresh token and access token, or
        UnknownClient if client_id is not a registered client.

        expires_at ends the grant. The tokens end at their own expiry, or
        with the grant if that comes first.
        """
        _require_grant_arguments(user_id, client_id, scope)
        now = int(_utc_now().timestamp())
        grant_expires_at = _expiry_timestamp("expires_at", expires_at, issued_at=now)
        refresh_token_expires_at_timestamp = _expiry_timestamp(
            "refresh_token_expires_at", refresh_token_expires_at, issued_at=now
        )
        access_token_expires_at_timestamp = _expiry_timestamp(
            "access_token_expires_at", access_token_expires_at, issued_at=now
        )

        with write_transaction(self._connection):
            inserted = self._insert_grant(
                user_id,
                client_id=client_id,
                resource=resource,
                scope=scope,
                now=now,
                expires_at=grant_expires_at,
            )
            if inserted.is_error():
                return Error(inserted.error)
            grant_id = inserted.ok
            tokens = self._issue_for_grant(
                grant_id,
                now,
                refresh_token_expires_at_timestamp,
                access_token_expires_at_timestamp,
            )
        return OK(tokens)

    def issue_delegated_token(
        self,
        user_id: UserId,
        *,
        resource: str | None,
        scope: frozenset[ScopeId],
        client_id: str,
        expires_at: datetime,
    ) -> Result[IssuedAccessToken, UnknownClient]:
        """An access token for a grant of the user without refresh tokens, or
        UnknownClient if client_id is not a registered client.

        A live grant of the same user, client, resource and scope is reused and
        extended to expires_at, and the access token expires then. Repeated
        requests keep extending the grant, so an expires_at a fixed time after
        each request acts as an idle timeout. Otherwise a new grant starts.
        Grants with refresh tokens are never reused.
        """
        _require_grant_arguments(user_id, client_id, scope)
        now = int(_utc_now().timestamp())
        grant_expires_at = _expiry_timestamp("expires_at", expires_at, issued_at=now)
        stored_scope = format_scopes(scope)
        # write_transaction takes the write lock before the lookup, so of two
        # concurrent requests the second finds the grant the first started.
        with write_transaction(self._connection):
            reused = self._connection.execute(
                """
                UPDATE grants SET expires_at = :grant_expires_at
                WHERE grant_id = (
                    SELECT grant_id FROM grants
                    WHERE user_id = :user_id AND client_id = :client_id
                        AND resource IS :resource AND scope = :scope
                        AND expires_at > :now
                        AND NOT EXISTS (
                            SELECT 1 FROM refresh_tokens
                            WHERE grant_id = grants.grant_id
                        )
                    ORDER BY created_at DESC
                    LIMIT 1
                )
                RETURNING grant_id
                """,
                {
                    "grant_expires_at": grant_expires_at,
                    "user_id": user_id,
                    "client_id": client_id,
                    "resource": resource,
                    "scope": stored_scope,
                    "now": now,
                },
            ).fetchone()
            if reused is not None:
                grant_id = reused["grant_id"]
            else:
                inserted = self._insert_grant(
                    user_id,
                    client_id=client_id,
                    resource=resource,
                    scope=scope,
                    now=now,
                    expires_at=grant_expires_at,
                )
                if inserted.is_error():
                    return Error(inserted.error)
                grant_id = inserted.ok
            access_token = self._insert_access_token(grant_id, now, grant_expires_at)
            self._purge(now)
        return OK(access_token)

    def rotate(
        self,
        refresh_token: str,
        *,
        refresh_token_expires_at: datetime,
        access_token_expires_at: datetime,
    ) -> IssuedTokens | None:
        """Retire refresh_token and issue its successor and a new access token.

        None if refresh_token is unknown, already rotated or expired;
        get_refresh_token tells these apart.
        """
        now = int(_utc_now().timestamp())
        refresh_token_expires_at_timestamp = _expiry_timestamp(
            "refresh_token_expires_at", refresh_token_expires_at, issued_at=now
        )
        access_token_expires_at_timestamp = _expiry_timestamp(
            "access_token_expires_at", access_token_expires_at, issued_at=now
        )
        try:
            token_hash = _refresh_token_hash(refresh_token)
        except ValueError:
            return None

        with write_transaction(self._connection):
            # One conditional UPDATE instead of read-then-write, so of two
            # concurrent rotations of the same token exactly one wins.
            rotated = self._connection.execute(
                """
                UPDATE refresh_tokens SET rotated_at = :now
                WHERE token_hash = :token_hash
                    AND rotated_at IS NULL
                    AND expires_at > :now
                RETURNING grant_id
                """,
                {"now": now, "token_hash": token_hash},
            ).fetchall()
            if not rotated:
                return None
            return self._issue_for_grant(
                rotated[0]["grant_id"],
                now,
                refresh_token_expires_at_timestamp,
                access_token_expires_at_timestamp,
            )

    def revoke_grant(self, grant_id: str) -> None:
        """End the grant, deleting it with all of its refresh and access tokens."""
        with write_transaction(self._connection):
            self._connection.execute("DELETE FROM grants WHERE grant_id = ?", (grant_id,))

    def list_usable_grants(self, user_id: UserId) -> list[GrantRecord]:
        """The user's grants a client can still use, newest first.

        A grant is usable while it has an unexpired, unrotated refresh token
        or an unexpired access token. Tokens never outlive their grant, so
        this also leaves out grants past their end before they are purged.

        Grants of built-in clients are left out: they are short-lived and the
        control plane re-creates them on each turn, so they are not the
        user's to manage and removing one achieves nothing lasting. Built-in
        clients are the ones without redirect URIs, which registration
        requires.
        """
        return self._list_usable_grants(user_id)

    def list_all_usable_grants(self) -> list[GrantRecord]:
        """The usable grants of every user, newest first, without built-in clients' grants."""
        return self._list_usable_grants(None)

    def _list_usable_grants(self, user_id: UserId | None) -> list[GrantRecord]:
        rows = self._connection.execute(
            f"""
            SELECT
                grant_id, user_id, client_id, resource, scope, created_at,
                expires_at AS grant_expires_at
            FROM grants
            WHERE {"user_id = :user_id AND" if user_id is not None else ""}
                EXISTS (
                    SELECT 1 FROM clients
                    WHERE client_id = grants.client_id AND redirect_uris != '[]'
                )
                AND (
                    EXISTS (
                        SELECT 1 FROM refresh_tokens
                        WHERE grant_id = grants.grant_id
                            AND rotated_at IS NULL AND expires_at > :now
                    )
                    OR EXISTS (
                        SELECT 1 FROM tokens
                        WHERE grant_id = grants.grant_id AND expires_at > :now
                    )
                )
            ORDER BY created_at DESC
            """,  # nosec B608
            {"now": int(_utc_now().timestamp())}
            | ({"user_id": user_id} if user_id is not None else {}),
        ).fetchall()
        return [grant for row in rows if (grant := _row_to_grant(row)) is not None]

    def revoke_grants(self, grant_ids: Collection[str], user_id: UserId) -> int:
        """End the given grants of the user, and return how many were actually deleted.

        Scoping the deletion to the user is the authorization check for the
        self-service page, independent of whatever the caller already filtered
        the displayed list by.
        """
        unique_ids = set(grant_ids)
        if not unique_ids:
            return 0

        with write_transaction(self._connection):
            cursor = self._connection.executemany(
                "DELETE FROM grants WHERE grant_id = ? AND user_id = ?",
                [(grant_id, user_id) for grant_id in unique_ids],
            )
        return cursor.rowcount

    def revoke_any_grants(self, grant_ids: Collection[str]) -> int:
        """End the given grants whoever owns them, and return how many were deleted."""
        unique_ids = set(grant_ids)
        if not unique_ids:
            return 0

        with write_transaction(self._connection):
            cursor = self._connection.executemany(
                "DELETE FROM grants WHERE grant_id = ?",
                [(grant_id,) for grant_id in unique_ids],
            )
        return cursor.rowcount

    def get_refresh_token(self, refresh_token: str) -> RefreshTokenRecord | None:
        try:
            token_hash = _refresh_token_hash(refresh_token)
        except ValueError:
            return None

        row = self._connection.execute(
            """
            SELECT
                r.issued_at, r.expires_at, r.rotated_at,
                g.grant_id, g.user_id, g.client_id, g.resource, g.scope,
                g.created_at, g.expires_at AS grant_expires_at
            FROM refresh_tokens AS r JOIN grants AS g USING (grant_id)
            WHERE r.token_hash = ?
            """,
            (token_hash,),
        ).fetchone()
        if row is None:
            return None

        grant = _row_to_grant(row)
        if grant is None:
            return None

        return RefreshTokenRecord(
            issued_at=_from_timestamp(row["issued_at"]),
            expires_at=_from_timestamp(row["expires_at"]),
            rotated_at=_optional_from_timestamp(row["rotated_at"]),
            grant=grant,
        )

    def _insert_grant(
        self,
        user_id: UserId,
        *,
        client_id: str,
        resource: str | None,
        scope: frozenset[ScopeId],
        now: int,
        expires_at: int,
    ) -> Result[str, UnknownClient]:
        """Insert a grant within the caller's write transaction."""
        grant_id = secrets.token_urlsafe(32)
        try:
            self._connection.execute(
                """
                INSERT INTO grants
                    (grant_id, user_id, client_id, resource, scope, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (grant_id, user_id, client_id, resource, format_scopes(scope), now, expires_at),
            )
        except sqlite3.IntegrityError:
            # _require_grant_arguments leaves the client_id foreign key as the
            # only constraint left to trip.
            logger.exception(
                "Refusing to start an OAuth grant: client %(client_id)s is not registered",
                {"client_id": client_id},
            )
            return Error(UnknownClient())
        return OK(grant_id)

    def _issue_for_grant(
        self, grant_id: str, now: int, refresh_token_expires_at: int, access_token_expires_at: int
    ) -> IssuedTokens:
        """Must run inside a write_transaction."""
        refresh_token = _mint_token(_REFRESH_TOKEN_PREFIX)
        # Both tokens are capped at the grant's expiry: no refresh token
        # outlives its grant, so an expired grant needs no separate check on
        # rotation, and no access token keeps a session alive past it.
        self._connection.execute(
            """
            INSERT INTO refresh_tokens (token_hash, grant_id, issued_at, expires_at)
            SELECT ?, grant_id, ?, MIN(?, expires_at) FROM grants WHERE grant_id = ?
            """,
            (_refresh_token_hash(refresh_token), now, refresh_token_expires_at, grant_id),
        )
        access_token = self._insert_access_token(grant_id, now, access_token_expires_at)
        self._purge(now)
        return IssuedTokens(
            access=access_token.access,
            expires_in=access_token.expires_in,
            refresh=refresh_token,
        )

    def _insert_access_token(
        self, grant_id: str, now: int, access_token_expires_at: int
    ) -> IssuedAccessToken:
        """Must run inside a write_transaction."""
        access_token = _mint_token(_ACCESS_TOKEN_PREFIX)
        (stored_expires_at,) = self._connection.execute(
            """
            INSERT INTO tokens
                (token_hash, user_id, issued_at, expires_at, resource, scope, client_id, grant_id)
            SELECT ?, user_id, ?, MIN(?, expires_at), resource, scope, client_id, grant_id
            FROM grants WHERE grant_id = ?
            RETURNING expires_at
            """,
            (_access_token_hash(access_token), now, access_token_expires_at, grant_id),
        ).fetchone()
        return IssuedAccessToken(access=access_token, expires_in=stored_expires_at - now)

    def _purge(self, now: int) -> None:
        """Delete expired tokens, then the grants left with no tokens at all.

        Must run inside a write_transaction, after the issuing step inserted
        its own tokens. Tokens issued before grants existed have no grant_id.
        """
        expired = self._connection.execute(
            "DELETE FROM tokens WHERE expires_at <= ? RETURNING grant_id", (now,)
        ).fetchall()
        purged = self._connection.execute(
            "DELETE FROM refresh_tokens WHERE expires_at < ? RETURNING grant_id",
            (now - int(_REFRESH_TOKEN_RETENTION.total_seconds()),),
        ).fetchall()
        # Only the grants that just lost a token can have become empty.
        self._connection.executemany(
            """
            DELETE FROM grants WHERE grant_id = ?
                AND NOT EXISTS (SELECT 1 FROM refresh_tokens WHERE grant_id = grants.grant_id)
                AND NOT EXISTS (SELECT 1 FROM tokens WHERE grant_id = grants.grant_id)
            """,
            {(row["grant_id"],) for row in (*expired, *purged) if row["grant_id"] is not None},
        )


@contextmanager
def get_token_store() -> Iterator[TokenStore]:
    """Get the token store, on a connection closed at the end of the with block."""
    with connect() as connection:
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
        token_hash=row["token_hash"],
        user_id=UserId(row["user_id"]),
        issued_at=_from_timestamp(row["issued_at"]),
        expires_at=_from_timestamp(row["expires_at"]),
        resource=row["resource"],
        scope=scope,
        client_id=row["client_id"],
        grant_id=row["grant_id"],
    )


def _row_to_grant(row: sqlite3.Row) -> GrantRecord | None:
    """The row as a record, or None if its scope is not one we could have written."""
    try:
        scope = parse_scopes(row["scope"] or "")
    except InvalidScopeError:
        logger.warning(
            "Refusing OAuth grant of user %(user_id)s: stored scope %(scope)r is not usable",
            {"user_id": row["user_id"], "scope": row["scope"]},
        )
        return None

    return GrantRecord(
        grant_id=row["grant_id"],
        user_id=UserId(row["user_id"]),
        client_id=row["client_id"],
        resource=row["resource"],
        scope=scope,
        created_at=_from_timestamp(row["created_at"]),
        expires_at=_from_timestamp(row["grant_expires_at"]),
    )


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _from_timestamp(value: int) -> datetime:
    return datetime.fromtimestamp(value, tz=UTC)


def _optional_from_timestamp(value: int | None) -> datetime | None:
    return None if value is None else _from_timestamp(value)


def _to_timestamp(value: datetime) -> int:
    if value.tzinfo is None:
        raise ValueError("datetime values must be timezone-aware")
    return int(value.astimezone(UTC).timestamp())


def _expiry_timestamp(name: str, value: datetime, *, issued_at: int) -> int:
    timestamp = _to_timestamp(value)
    if timestamp <= issued_at:
        raise ValueError(f"{name} must be later than the issue time")
    return timestamp


def _access_token_hash(token: str) -> str:
    return _prefixed_token_hash(token, _ACCESS_TOKEN_PREFIX)


def _refresh_token_hash(token: str) -> str:
    return _prefixed_token_hash(token, _REFRESH_TOKEN_PREFIX)


def _prefixed_token_hash(token: str, prefix: str) -> str:
    if not _has_prefix(token, prefix):
        raise ValueError("not a well-formed token")
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
