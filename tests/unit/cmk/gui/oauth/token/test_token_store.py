#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import hashlib
import logging
import sqlite3
import threading
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, UTC
from pathlib import Path

import pytest
import time_machine

from cmk.ccc.resulttype import Error
from cmk.ccc.user import UserId
from cmk.gui.oauth.store.client_store import ClientId, ClientStore
from cmk.gui.oauth.token.token_store import (
    IssuedAccessToken,
    IssuedTokens,
    TokenRecord,
    TokenStore,
    UnknownClient,
)
from cmk.gui.scopes import DEFAULT_SCOPE, ScopeId
from cmk.schema_manager import ensure_schema
from cmk.schema_migrations.oauth import schema_manager_oauth
from cmk.testlib.schema_manager import migrated_connection

_USER = UserId("cmkadmin")
_CLIENT = "test-client"
_GRANT_ID = "Hq3vTn8xWbL2kEe5RmYc0sPz7uJdA9fGiOw4NtK1lMQ"
_RESOURCE = "https://example.test/api"


_GRANT_LIFETIME = timedelta(days=365)
_IDLE_TIMEOUT = timedelta(days=30)
_ACCESS_TOKEN_TTL = timedelta(hours=48)


def _register_client(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT INTO clients (client_id, redirect_uris, client_name, registered_at)
        VALUES (?, '["https://client.example/callback"]', NULL, 0)
        """,
        (_CLIENT,),
    )


@pytest.fixture
def connection() -> Iterator[sqlite3.Connection]:
    with migrated_connection(schema_manager_oauth) as connection:
        _register_client(connection)
        yield connection


@pytest.fixture
def store(connection: sqlite3.Connection) -> TokenStore:
    return TokenStore(connection)


def _future(minutes: int) -> datetime:
    return (datetime.now(UTC) + timedelta(minutes=minutes)).replace(microsecond=0)


def _past(minutes: int) -> datetime:
    return (datetime.now(UTC) - timedelta(minutes=minutes)).replace(microsecond=0)


def _overwrite_stored_scope(
    connection: sqlite3.Connection, token: str, raw_scope: str | None
) -> None:
    """Put a value in the scope column that this version would never write there."""
    connection.execute(
        "UPDATE tokens SET scope = ? WHERE token_hash = ?",
        (raw_scope, hashlib.sha256(token.encode("utf-8")).hexdigest()),
    )


# TokenRecord.is_valid


def test_record_is_valid_before_it_expires() -> None:
    record = TokenRecord(
        token_hash="deadbeef",
        user_id=_USER,
        issued_at=_past(5),
        expires_at=_future(5),
        resource=None,
        scope=DEFAULT_SCOPE,
        client_id=_CLIENT,
        grant_id=_GRANT_ID,
    )

    assert record.is_valid(at=_future(1)) is True


def test_record_is_not_valid_after_it_expires() -> None:
    record = TokenRecord(
        token_hash="deadbeef",
        user_id=_USER,
        issued_at=_past(10),
        expires_at=_past(5),
        resource=None,
        scope=DEFAULT_SCOPE,
        client_id=_CLIENT,
        grant_id=_GRANT_ID,
    )

    assert record.is_valid(at=datetime.now(UTC)) is False


def test_record_is_valid_defaults_to_the_current_time() -> None:
    record = TokenRecord(
        token_hash="deadbeef",
        user_id=_USER,
        issued_at=_past(5),
        expires_at=_future(60),
        resource=None,
        scope=DEFAULT_SCOPE,
        client_id=_CLIENT,
        grant_id=_GRANT_ID,
    )

    assert record.is_valid() is True


def test_record_is_valid_rejects_naive_datetimes() -> None:
    record = TokenRecord(
        token_hash="deadbeef",
        user_id=_USER,
        issued_at=_past(5),
        expires_at=_future(5),
        resource=None,
        scope=DEFAULT_SCOPE,
        client_id=_CLIENT,
        grant_id=_GRANT_ID,
    )

    with pytest.raises(ValueError, match="timezone-aware"):
        record.is_valid(at=datetime.now())


# Grants and refresh tokens


def _start_grant(
    store: TokenStore,
    *,
    user_id: UserId = _USER,
    grant_lifetime: timedelta = _GRANT_LIFETIME,
    idle_timeout: timedelta = _IDLE_TIMEOUT,
) -> IssuedTokens:
    now = datetime.now(UTC)
    issued = store.start_grant(
        user_id,
        resource=_RESOURCE,
        scope=DEFAULT_SCOPE,
        client_id=_CLIENT,
        expires_at=now + grant_lifetime,
        refresh_token_expires_at=now + idle_timeout,
        access_token_expires_at=now + _ACCESS_TOKEN_TTL,
    )
    assert issued.is_ok()
    return issued.ok


def _rotate(
    store: TokenStore, refresh_token: str, idle_timeout: timedelta = _IDLE_TIMEOUT
) -> IssuedTokens | None:
    now = datetime.now(UTC)
    return store.rotate(
        refresh_token,
        refresh_token_expires_at=now + idle_timeout,
        access_token_expires_at=now + _ACCESS_TOKEN_TTL,
    )


def _grant_id(store: TokenStore, refresh_token: str) -> str:
    record = store.get_refresh_token(refresh_token)
    assert record is not None
    return record.grant.grant_id


def _row_counts(connection: sqlite3.Connection) -> dict[str, int]:
    return {
        table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]  # nosec B608
        for table in ("grants", "refresh_tokens", "tokens")
    }


def _fail_access_token_inserts(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TRIGGER fail_access_token_insert BEFORE INSERT ON tokens
        BEGIN SELECT RAISE(ABORT, 'injected failure'); END
        """
    )


_OTHER_CLIENT = "other-client"
_DELEGATE_LIFETIME = timedelta(hours=1)
_AT = datetime(2026, 3, 1, tzinfo=UTC)


def _delegate(
    store: TokenStore,
    *,
    user_id: UserId = _USER,
    resource: str | None = _RESOURCE,
    scope: frozenset[ScopeId] = DEFAULT_SCOPE,
    client_id: str = _CLIENT,
) -> IssuedAccessToken:
    issued = store.issue_delegated_token(
        user_id,
        resource=resource,
        scope=scope,
        client_id=client_id,
        expires_at=datetime.now(UTC) + _DELEGATE_LIFETIME,
    )
    assert issued.is_ok()
    return issued.ok


def _access_token_record(store: TokenStore, access_token: str) -> TokenRecord:
    record = store.get_by_token(access_token)
    assert record is not None
    return record


def _grant_of(store: TokenStore, access_token: str) -> str:
    grant_id = _access_token_record(store, access_token).grant_id
    assert grant_id is not None
    return grant_id


def _register_other_client(connection: sqlite3.Connection) -> None:
    connection.execute(
        "INSERT INTO clients (client_id, redirect_uris, client_name, registered_at)"
        " VALUES (?, '[]', NULL, 0)",
        (_OTHER_CLIENT,),
    )


def _grant_ids(connection: sqlite3.Connection) -> set[str]:
    return {row[0] for row in connection.execute("SELECT grant_id FROM grants")}


# TokenStore.get_by_token


def test_get_by_token_returns_the_record_of_the_issued_token(store: TokenStore) -> None:
    with time_machine.travel(_AT, tick=False):
        issued = _delegate(store, scope=frozenset({ScopeId.WRITE}))

        record = store.get_by_token(issued.access)

    assert record is not None
    assert (record.user_id, record.resource, record.scope, record.client_id) == (
        _USER,
        _RESOURCE,
        frozenset({ScopeId.READ, ScopeId.WRITE}),
        _CLIENT,
    )
    assert record.expires_at == _AT + _DELEGATE_LIFETIME


def test_get_by_token_returns_none_for_an_unknown_token(store: TokenStore) -> None:
    assert store.get_by_token("never-issued") is None


@pytest.mark.parametrize("stored_scope", ["mcp", None])
def test_get_by_token_refuses_a_token_whose_stored_scope_does_not_parse(
    store: TokenStore, connection: sqlite3.Connection, stored_scope: str | None
) -> None:
    issued = _delegate(store)
    _overwrite_stored_scope(connection, issued.access, stored_scope)

    assert store.get_by_token(issued.access) is None


# TokenStore.issue_delegated_token


def test_a_delegated_token_belongs_to_a_grant_that_ends_with_it(store: TokenStore) -> None:
    with time_machine.travel(_AT, tick=False):
        issued = _delegate(store)

        record = _access_token_record(store, issued.access)
        (grant,) = store.list_usable_grants(_USER)

    assert (grant.grant_id, grant.user_id, grant.client_id) == (record.grant_id, _USER, _CLIENT)
    assert (grant.created_at, grant.expires_at) == (_AT, _AT + _DELEGATE_LIFETIME)
    assert record.expires_at == grant.expires_at
    assert issued.expires_in == int(_DELEGATE_LIFETIME.total_seconds())


def test_a_repeated_delegated_request_extends_the_same_grant(store: TokenStore) -> None:
    with time_machine.travel(_AT, tick=False):
        first = _delegate(store)
    with time_machine.travel(_AT + timedelta(minutes=30), tick=False):
        second = _delegate(store)

        (grant,) = store.list_usable_grants(_USER)

    assert _grant_of(store, first.access) == grant.grant_id
    assert _grant_of(store, second.access) == grant.grant_id
    assert grant.created_at == _AT
    assert grant.expires_at == _AT + timedelta(minutes=30) + _DELEGATE_LIFETIME
    assert second.expires_in == int(_DELEGATE_LIFETIME.total_seconds())


def test_a_delegated_request_after_the_grant_ended_starts_a_new_grant(store: TokenStore) -> None:
    with time_machine.travel(_AT, tick=False):
        first_grant_id = _grant_of(store, _delegate(store).access)
    with time_machine.travel(_AT + _DELEGATE_LIFETIME, tick=False):
        second = _delegate(store)

        (grant,) = store.list_usable_grants(_USER)

    assert grant.grant_id != first_grant_id
    assert _grant_of(store, second.access) == grant.grant_id


@dataclass(frozen=True)
class _Arguments:
    user_id: UserId = _USER
    client_id: str = _CLIENT
    resource: str | None = _RESOURCE
    scope: frozenset[ScopeId] = DEFAULT_SCOPE
    expires_at: datetime = _AT + _DELEGATE_LIFETIME


@pytest.mark.parametrize(
    "other",
    [
        pytest.param(_Arguments(resource="https://host/other/check_mk/mcp"), id="resource"),
        pytest.param(_Arguments(resource=None), id="no resource"),
        pytest.param(_Arguments(scope=frozenset({ScopeId.WRITE})), id="scope"),
        pytest.param(_Arguments(user_id=UserId("other")), id="user"),
        pytest.param(_Arguments(client_id=_OTHER_CLIENT), id="client"),
    ],
)
def test_a_delegated_request_for_another_key_starts_a_new_grant(
    store: TokenStore, connection: sqlite3.Connection, other: _Arguments
) -> None:
    _register_other_client(connection)
    first = _delegate(store)

    second = _delegate(
        store,
        user_id=other.user_id,
        resource=other.resource,
        scope=other.scope,
        client_id=other.client_id,
    )

    assert _grant_of(store, first.access) != _grant_of(store, second.access)


def test_a_delegated_request_does_not_reuse_a_grant_with_refresh_tokens(
    store: TokenStore,
) -> None:
    started = _start_grant(store)

    issued = _delegate(store)

    assert _grant_of(store, issued.access) != _grant_id(store, started.refresh)


def _start_grant_with(store: TokenStore, arguments: _Arguments) -> object:
    return store.start_grant(
        arguments.user_id,
        resource=arguments.resource,
        scope=arguments.scope,
        client_id=arguments.client_id,
        expires_at=arguments.expires_at,
        refresh_token_expires_at=arguments.expires_at,
        access_token_expires_at=arguments.expires_at,
    )


def _delegate_with(store: TokenStore, arguments: _Arguments) -> object:
    return store.issue_delegated_token(
        arguments.user_id,
        resource=arguments.resource,
        scope=arguments.scope,
        client_id=arguments.client_id,
        expires_at=arguments.expires_at,
    )


@pytest.mark.parametrize("issue", [_start_grant_with, _delegate_with])
@pytest.mark.parametrize(
    "invalid",
    [
        pytest.param(_Arguments(user_id=UserId("")), id="empty user"),
        pytest.param(_Arguments(client_id=""), id="empty client"),
        pytest.param(_Arguments(scope=frozenset()), id="empty scope"),
        pytest.param(_Arguments(expires_at=_AT - timedelta(seconds=1)), id="expiry in the past"),
        pytest.param(_Arguments(expires_at=_AT), id="expiry now"),
        pytest.param(_Arguments(expires_at=_AT.replace(tzinfo=None)), id="naive expiry"),
    ],
)
def test_issuing_refuses_invalid_arguments(
    store: TokenStore,
    issue: Callable[[TokenStore, _Arguments], object],
    invalid: _Arguments,
) -> None:
    with time_machine.travel(_AT, tick=False), pytest.raises(ValueError):
        issue(store, invalid)


def test_concurrent_delegated_requests_for_one_key_leave_one_grant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OMD_ROOT", str(tmp_path))
    ensure_schema(schema_manager_oauth, logging.getLogger(__name__))
    with schema_manager_oauth.connect() as connection:
        _register_client(connection)
    both_connected = threading.Barrier(2)

    def delegate_on_own_connection() -> IssuedAccessToken:
        with schema_manager_oauth.connect() as connection:
            both_connected.wait()
            return _delegate(TokenStore(connection))

    with ThreadPoolExecutor(max_workers=2) as executor:
        issued = list(executor.map(lambda _: delegate_on_own_connection(), range(2)))

    with schema_manager_oauth.connect() as connection:
        store = TokenStore(connection)
        grant_ids = {_grant_of(store, i.access) for i in issued}
        assert len(grant_ids) == 1


def test_revoking_a_delegated_grant_ends_all_its_access_tokens(store: TokenStore) -> None:
    first = _delegate(store)
    second = _delegate(store)

    store.revoke_grant(_grant_of(store, first.access))

    assert store.get_by_token(first.access) is None
    assert store.get_by_token(second.access) is None


def test_issuing_a_delegated_token_deletes_the_expired_access_tokens_of_every_client(
    store: TokenStore, connection: sqlite3.Connection
) -> None:
    _register_other_client(connection)
    with time_machine.travel(_AT, tick=False):
        expired = _delegate(store, client_id=_OTHER_CLIENT)
    with time_machine.travel(_AT + timedelta(minutes=30), tick=False):
        kept = _delegate(store, user_id=UserId("other"))
    with time_machine.travel(_AT + _DELEGATE_LIFETIME, tick=False):
        _delegate(store)

        assert store.get_by_token(expired.access) is None
        assert store.get_by_token(kept.access) is not None


def test_issuing_a_delegated_token_refuses_an_unregistered_client(store: TokenStore) -> None:
    issued = store.issue_delegated_token(
        _USER,
        resource=None,
        scope=DEFAULT_SCOPE,
        client_id="never-registered",
        expires_at=datetime.now(UTC) + _DELEGATE_LIFETIME,
    )

    assert issued == Error(UnknownClient())


def test_a_refresh_token_is_not_stored_in_plaintext(
    store: TokenStore, connection: sqlite3.Connection
) -> None:
    refresh_token = _start_grant(store).refresh

    stored = [row[0] for row in connection.execute("SELECT token_hash FROM refresh_tokens")]

    assert stored
    assert refresh_token not in stored


def test_an_access_token_is_not_accepted_as_a_refresh_token(store: TokenStore) -> None:
    issued = _start_grant(store)

    assert store.get_refresh_token(issued.access) is None


def test_a_refresh_token_is_not_accepted_as_an_access_token(store: TokenStore) -> None:
    issued = _start_grant(store)

    assert store.get_by_token(issued.refresh) is None


def test_start_grant_rejects_an_unregistered_client(store: TokenStore) -> None:
    now = datetime.now(UTC)
    issued = store.start_grant(
        _USER,
        resource=None,
        scope=DEFAULT_SCOPE,
        client_id="never-registered",
        expires_at=now + _GRANT_LIFETIME,
        refresh_token_expires_at=now + _IDLE_TIMEOUT,
        access_token_expires_at=now + _ACCESS_TOKEN_TTL,
    )

    assert issued == Error(UnknownClient())


def test_a_rotated_token_expires_one_idle_timeout_after_its_own_issuance(
    store: TokenStore,
) -> None:
    rotated_at = datetime(2026, 3, 1, tzinfo=UTC)
    with time_machine.travel(rotated_at - timedelta(days=10), tick=False):
        refresh_token = _start_grant(store).refresh
    with time_machine.travel(rotated_at, tick=False):
        successor = _rotate(store, refresh_token)
    assert successor is not None

    record = store.get_refresh_token(successor.refresh)

    assert record is not None
    assert record.expires_at == rotated_at + _IDLE_TIMEOUT


def test_a_grant_that_keeps_being_rotated_ends_at_its_lifetime(store: TokenStore) -> None:
    started_at = datetime(2026, 3, 1, tzinfo=UTC)
    with time_machine.travel(started_at, tick=False):
        refresh_token = _start_grant(store, grant_lifetime=timedelta(days=60)).refresh
    for day in (20, 40, 59):
        with time_machine.travel(started_at + timedelta(days=day), tick=False):
            successor = _rotate(store, refresh_token)
        assert successor is not None
        refresh_token = successor.refresh

    # The end of the grant's 60-day lifetime.
    with time_machine.travel(started_at + timedelta(days=60), tick=False):
        assert _rotate(store, refresh_token) is None


def test_an_access_token_issued_shortly_before_the_grant_ends_ends_with_it(
    store: TokenStore,
) -> None:
    started_at = datetime(2026, 3, 1, tzinfo=UTC)
    with time_machine.travel(started_at, tick=False):
        refresh_token = _start_grant(store, grant_lifetime=timedelta(days=20)).refresh
    with time_machine.travel(started_at + timedelta(days=19, hours=12), tick=False):
        successor = _rotate(store, refresh_token)
    assert successor is not None
    assert successor.expires_in == 12 * 3600

    record = store.get_by_token(successor.access)
    assert record is not None
    assert not record.is_valid(at=started_at + timedelta(days=20))


def test_concurrent_rotations_of_the_same_token_yield_exactly_one_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OMD_ROOT", str(tmp_path))
    ensure_schema(schema_manager_oauth, logging.getLogger(__name__))
    with schema_manager_oauth.connect() as connection:
        _register_client(connection)
        refresh_token = _start_grant(TokenStore(connection)).refresh
    both_connected = threading.Barrier(2)

    def rotate_on_own_connection() -> IssuedTokens | None:
        with schema_manager_oauth.connect() as connection:
            both_connected.wait()
            return _rotate(TokenStore(connection), refresh_token)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: rotate_on_own_connection(), range(2)))

    assert sorted(result is not None for result in results) == [False, True]


def test_revoking_a_grant_ends_its_refresh_and_access_tokens(store: TokenStore) -> None:
    issued = _start_grant(store)

    store.revoke_grant(_grant_id(store, issued.refresh))

    assert store.get_refresh_token(issued.refresh) is None
    assert store.get_by_token(issued.access) is None


def test_a_failed_start_grant_leaves_no_rows_behind(
    store: TokenStore, connection: sqlite3.Connection
) -> None:
    _fail_access_token_inserts(connection)

    with pytest.raises(sqlite3.IntegrityError, match="injected failure"):
        _start_grant(store)

    assert _row_counts(connection) == {"grants": 0, "refresh_tokens": 0, "tokens": 0}


def test_a_failed_rotation_leaves_no_rows_behind(
    store: TokenStore, connection: sqlite3.Connection
) -> None:
    refresh_token = _start_grant(store).refresh
    _fail_access_token_inserts(connection)

    with pytest.raises(sqlite3.IntegrityError, match="injected failure"):
        _rotate(store, refresh_token)

    record = store.get_refresh_token(refresh_token)
    assert record is not None
    assert record.rotated_at is None


def test_issuing_purges_refresh_tokens_expired_beyond_the_retention_period(
    store: TokenStore,
) -> None:
    started_at = datetime(2026, 3, 1, tzinfo=UTC)
    with time_machine.travel(started_at, tick=False):
        first = _start_grant(store).refresh
    with time_machine.travel(started_at + timedelta(days=1), tick=False):
        successor = _rotate(store, first)
    assert successor is not None
    with time_machine.travel(started_at + timedelta(days=59), tick=False):
        other = _start_grant(store).refresh

    # first expired 30.5 days ago, successor 29.5 days ago.
    with time_machine.travel(started_at + timedelta(days=60, hours=12), tick=False):
        assert _rotate(store, other) is not None

    assert store.get_refresh_token(first) is None
    assert store.get_refresh_token(successor.refresh) is not None


def test_a_grant_is_purged_only_once_neither_refresh_nor_access_tokens_remain(
    store: TokenStore, connection: sqlite3.Connection
) -> None:
    started_at = datetime(2026, 3, 1, tzinfo=UTC)
    with time_machine.travel(started_at, tick=False):
        long_lived = store.start_grant(
            _USER,
            resource=None,
            scope=DEFAULT_SCOPE,
            client_id=_CLIENT,
            expires_at=started_at + _GRANT_LIFETIME,
            refresh_token_expires_at=started_at + timedelta(days=1),
            access_token_expires_at=started_at + timedelta(days=100),
        )
        assert long_lived.is_ok()
    grant_id = _grant_id(store, long_lived.ok.refresh)

    # The refresh token expired 39 days ago, the access token is valid for 60 more.
    with time_machine.travel(started_at + timedelta(days=40), tick=False):
        _start_grant(store)
        assert grant_id in _grant_ids(connection)

    with time_machine.travel(started_at + timedelta(days=100), tick=False):
        _start_grant(store)
        assert grant_id not in _grant_ids(connection)


# TokenStore.list_usable_grants


def test_a_listed_grant_carries_client_scope_resource_and_start_time(store: TokenStore) -> None:
    started_at = _future(0)
    with time_machine.travel(started_at, tick=False):
        _start_grant(store)

    (grant,) = store.list_usable_grants(_USER)

    assert (grant.user_id, grant.client_id, grant.scope, grant.resource, grant.created_at) == (
        _USER,
        _CLIENT,
        DEFAULT_SCOPE,
        _RESOURCE,
        started_at,
    )


def test_list_usable_grants_returns_the_newest_grant_first(store: TokenStore) -> None:
    started_at = _future(0)
    grant_ids = []
    for hours in (0, 2, 1):
        with time_machine.travel(started_at + timedelta(hours=hours), tick=False):
            grant_ids.append(_grant_id(store, _start_grant(store).refresh))

    listed = [grant.grant_id for grant in store.list_usable_grants(_USER)]

    assert listed == [grant_ids[1], grant_ids[2], grant_ids[0]]


def test_list_usable_grants_of_a_user_leaves_out_other_users_grants(store: TokenStore) -> None:
    own = _grant_id(store, _start_grant(store).refresh)
    _start_grant(store, user_id=UserId("other"))

    assert [grant.grant_id for grant in store.list_usable_grants(_USER)] == [own]


def test_list_all_usable_grants_returns_every_users_grants(store: TokenStore) -> None:
    own = _grant_id(store, _start_grant(store).refresh)
    other = _grant_id(store, _start_grant(store, user_id=UserId("other")).refresh)

    assert {grant.grant_id for grant in store.list_all_usable_grants()} == {own, other}


def test_listing_leaves_out_the_grants_of_built_in_clients(
    store: TokenStore, connection: sqlite3.Connection
) -> None:
    ClientStore(connection).ensure_builtin(ClientId("builtin"), "Built-in")
    _delegate(store, client_id="builtin")
    registered = _delegate(store)

    expected = [_grant_of(store, registered.access)]
    assert [grant.grant_id for grant in store.list_usable_grants(_USER)] == expected
    assert [grant.grant_id for grant in store.list_all_usable_grants()] == expected


def test_list_usable_grants_skips_a_grant_whose_stored_scope_does_not_parse(
    store: TokenStore, connection: sqlite3.Connection
) -> None:
    _start_grant(store)
    unusable = _grant_id(store, _start_grant(store).refresh)
    connection.execute("UPDATE grants SET scope = 'mcp' WHERE grant_id = ?", (unusable,))

    assert len(store.list_usable_grants(_USER)) == 1


def test_a_grant_without_a_usable_token_is_not_listed(store: TokenStore) -> None:
    started_at = _future(0)
    with time_machine.travel(started_at, tick=False):
        _start_grant(store)

    with time_machine.travel(started_at + _IDLE_TIMEOUT + timedelta(seconds=1), tick=False):
        assert store.list_usable_grants(_USER) == []


def test_a_rotated_refresh_token_does_not_keep_its_grant_listed(store: TokenStore) -> None:
    started_at = _future(0)
    with time_machine.travel(started_at, tick=False):
        refresh_token = _start_grant(store).refresh
    with time_machine.travel(started_at + timedelta(hours=1), tick=False):
        assert _rotate(store, refresh_token, idle_timeout=timedelta(hours=1)) is not None

    with time_machine.travel(started_at + timedelta(hours=1) + _ACCESS_TOKEN_TTL, tick=False):
        assert store.list_usable_grants(_USER) == []


def test_a_grant_with_expired_access_tokens_is_listed_while_its_refresh_token_is_valid(
    store: TokenStore,
) -> None:
    started_at = _future(0)
    with time_machine.travel(started_at, tick=False):
        _start_grant(store)

    with time_machine.travel(started_at + _ACCESS_TOKEN_TTL + timedelta(hours=1), tick=False):
        assert len(store.list_usable_grants(_USER)) == 1


def test_a_grant_without_refresh_tokens_is_listed_while_its_access_token_is_valid(
    store: TokenStore,
) -> None:
    with time_machine.travel(_AT, tick=False):
        _delegate(store)

    with time_machine.travel(_AT + _DELEGATE_LIFETIME - timedelta(seconds=1), tick=False):
        assert len(store.list_usable_grants(_USER)) == 1
    with time_machine.travel(_AT + _DELEGATE_LIFETIME, tick=False):
        assert store.list_usable_grants(_USER) == []


# TokenStore.revoke_grants


def test_revoke_grants_ends_the_given_grants_only(store: TokenStore) -> None:
    first = _start_grant(store)
    second = _start_grant(store)
    kept = _start_grant(store)

    deleted = store.revoke_grants(
        [_grant_id(store, first.refresh), _grant_id(store, second.refresh)], _USER
    )

    assert deleted == 2
    assert store.get_by_token(first.access) is None
    assert store.get_refresh_token(second.refresh) is None
    assert store.get_by_token(kept.access) is not None


def test_revoke_grants_does_not_end_another_users_grant(
    store: TokenStore,
) -> None:
    other = _start_grant(store, user_id=UserId("other"))

    deleted = store.revoke_grants([_grant_id(store, other.refresh)], _USER)

    assert deleted == 0
    assert store.get_refresh_token(other.refresh) is not None


def test_revoke_any_grants_ends_grants_of_every_user(store: TokenStore) -> None:
    own = _start_grant(store)
    other = _start_grant(store, user_id=UserId("other"))
    kept = _start_grant(store)

    deleted = store.revoke_any_grants(
        [_grant_id(store, own.refresh), _grant_id(store, other.refresh)]
    )

    assert deleted == 2
    assert store.get_refresh_token(own.refresh) is None
    assert store.get_refresh_token(other.refresh) is None
    assert store.get_refresh_token(kept.refresh) is not None
