#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import sqlite3
import threading
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, UTC
from pathlib import Path

import pytest
import time_machine

from cmk.ccc.resulttype import Error
from cmk.ccc.user import UserId
from cmk.gui.oauth.token.token_store import (
    _access_token_hash,
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


def _overwrite_stored_scope(store: TokenStore, token: str, raw_scope: str | None) -> None:
    """Put a value in the scope column that this version would never write there."""
    store._connection.execute(  # noqa: SLF001
        "UPDATE tokens SET scope = ? WHERE token_hash = ?",
        (raw_scope, _access_token_hash(token)),
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


# TokenStore.issue_token


def test_issue_token_stores_only_a_hash_never_the_plaintext(store: TokenStore) -> None:
    token = store.issue_token(
        _USER, expires_at=_future(60), resource=None, scope=DEFAULT_SCOPE, client_id=_CLIENT
    )
    assert token.is_ok()

    stored_hashes = [row[0] for row in store._connection.execute("SELECT token_hash FROM tokens")]  # noqa: SLF001
    assert token.ok.access not in stored_hashes


def test_issue_token_produces_unique_tokens(store: TokenStore) -> None:
    first = store.issue_token(
        _USER, expires_at=_future(60), resource=None, scope=DEFAULT_SCOPE, client_id=_CLIENT
    )
    second = store.issue_token(
        _USER, expires_at=_future(60), resource=None, scope=DEFAULT_SCOPE, client_id=_CLIENT
    )
    assert first.is_ok()
    assert second.is_ok()

    assert first.ok.access != second.ok.access


def test_issue_token_rejects_an_empty_user_id(store: TokenStore) -> None:
    with pytest.raises(ValueError, match="user_id"):
        store.issue_token(
            UserId(""),
            expires_at=_future(60),
            resource=None,
            scope=DEFAULT_SCOPE,
            client_id=_CLIENT,
        )


def test_issue_token_rejects_an_expiry_in_the_past(store: TokenStore) -> None:
    with pytest.raises(ValueError, match="expires_at"):
        store.issue_token(
            _USER, expires_at=_past(5), resource=None, scope=DEFAULT_SCOPE, client_id=_CLIENT
        )


def test_issue_token_rejects_a_naive_expiry(store: TokenStore) -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        store.issue_token(
            _USER,
            expires_at=datetime.now() + timedelta(minutes=5),
            resource=None,
            scope=DEFAULT_SCOPE,
            client_id=_CLIENT,
        )


def test_issue_token_rejects_an_empty_client_id(store: TokenStore) -> None:
    with pytest.raises(ValueError, match="client_id"):
        store.issue_token(
            _USER, expires_at=_future(60), resource=None, scope=DEFAULT_SCOPE, client_id=""
        )


def test_issue_token_rejects_an_empty_scope(store: TokenStore) -> None:
    with pytest.raises(ValueError, match="scope"):
        store.issue_token(
            _USER, expires_at=_future(60), resource=None, scope=frozenset(), client_id=_CLIENT
        )


def test_issue_token_rejects_an_unregistered_client(store: TokenStore) -> None:
    token = store.issue_token(
        _USER,
        expires_at=_future(60),
        resource=None,
        scope=DEFAULT_SCOPE,
        client_id="never-registered",
    )

    assert token == Error(UnknownClient())


# TokenStore.get_by_token


def test_get_by_token_returns_the_matching_record(store: TokenStore) -> None:
    issued_at = _future(0)

    with time_machine.travel(issued_at, tick=False):
        token = store.issue_token(
            _USER,
            expires_at=issued_at + timedelta(minutes=60),
            resource=None,
            scope=DEFAULT_SCOPE,
            client_id=_CLIENT,
        )
    assert token.is_ok()

    record = store.get_by_token(token.ok.access)
    assert record is not None
    assert record.user_id == _USER
    assert record.expires_at == issued_at + timedelta(minutes=60)
    assert token.ok.expires_in == 3600


def test_get_by_token_returns_none_for_an_unknown_token(store: TokenStore) -> None:
    assert store.get_by_token("never-issued") is None


def test_get_by_token_returns_the_bound_resource(store: TokenStore) -> None:
    token = store.issue_token(
        _USER,
        expires_at=_future(60),
        resource="https://host/mysite/check_mk/mcp",
        scope=DEFAULT_SCOPE,
        client_id=_CLIENT,
    )
    assert token.is_ok()

    record = store.get_by_token(token.ok.access)
    assert record is not None
    assert record.resource == "https://host/mysite/check_mk/mcp"


def test_get_by_token_returns_none_for_an_unbound_resource(store: TokenStore) -> None:
    token = store.issue_token(
        _USER, expires_at=_future(60), resource=None, scope=DEFAULT_SCOPE, client_id=_CLIENT
    )
    assert token.is_ok()

    record = store.get_by_token(token.ok.access)
    assert record is not None
    assert record.resource is None


def test_get_by_token_returns_the_bound_scope(store: TokenStore) -> None:
    token = store.issue_token(
        _USER,
        expires_at=_future(60),
        resource=None,
        scope=frozenset({ScopeId.READ}),
        client_id=_CLIENT,
    )
    assert token.is_ok()

    record = store.get_by_token(token.ok.access)
    assert record is not None
    assert record.scope == {ScopeId.READ}
    assert store._connection.execute("SELECT scope FROM tokens").fetchone()[0] == "read"  # noqa: SLF001


@pytest.mark.parametrize("stored_scope", ["mcp", None])
def test_get_by_token_refuses_a_token_whose_stored_scope_does_not_parse(
    store: TokenStore, stored_scope: str | None
) -> None:
    token = store.issue_token(
        _USER, expires_at=_future(60), resource=None, scope=DEFAULT_SCOPE, client_id=_CLIENT
    )
    assert token.is_ok()
    _overwrite_stored_scope(store, token.ok.access, stored_scope)

    assert store.get_by_token(token.ok.access) is None


def test_get_by_token_returns_the_issuing_client(store: TokenStore) -> None:
    token = store.issue_token(
        _USER, expires_at=_future(60), resource=None, scope=DEFAULT_SCOPE, client_id=_CLIENT
    )
    assert token.is_ok()

    record = store.get_by_token(token.ok.access)
    assert record is not None
    assert record.client_id == _CLIENT


# TokenStore.list_all


def test_list_all_returns_empty_for_an_empty_store(store: TokenStore) -> None:
    assert store.list_all() == []


def test_list_all_returns_tokens_across_users(store: TokenStore) -> None:
    other_user = UserId("other")
    store.issue_token(
        other_user, expires_at=_future(60), resource=None, scope=DEFAULT_SCOPE, client_id=_CLIENT
    )
    store.issue_token(
        _USER, expires_at=_future(60), resource=None, scope=DEFAULT_SCOPE, client_id=_CLIENT
    )

    records = store.list_all()

    assert len(records) == 2
    assert {record.user_id for record in records} == {_USER, other_user}


def test_issue_token_deletes_expired_tokens_and_keeps_valid_ones(store: TokenStore) -> None:
    expiring = store.issue_token(
        _USER, expires_at=_future(1), resource=None, scope=DEFAULT_SCOPE, client_id=_CLIENT
    )
    lasting = store.issue_token(
        _USER, expires_at=_future(60), resource=None, scope=DEFAULT_SCOPE, client_id=_CLIENT
    )
    assert expiring.is_ok()
    assert lasting.is_ok()

    with time_machine.travel(_future(5)):
        store.issue_token(
            _USER, expires_at=_future(60), resource=None, scope=DEFAULT_SCOPE, client_id=_CLIENT
        )

    assert store.get_by_token(expiring.ok.access) is None
    assert store.get_by_token(lasting.ok.access) is not None


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
        resource="https://example.test/api",
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


def test_a_grant_is_purged_only_once_none_of_its_refresh_tokens_remain(
    store: TokenStore, connection: sqlite3.Connection
) -> None:
    started_at = datetime(2026, 3, 1, tzinfo=UTC)
    with time_machine.travel(started_at, tick=False):
        _start_grant(store)
        rotated = _start_grant(store).refresh
    with time_machine.travel(started_at + timedelta(days=10), tick=False):
        successor = _rotate(store, rotated)
    assert successor is not None
    kept_grant_id = _grant_id(store, successor.refresh)

    # Both initial tokens expired 35 days ago, the successor 25 days ago.
    with time_machine.travel(started_at + timedelta(days=65), tick=False):
        new_grant_id = _grant_id(store, _start_grant(store).refresh)

    assert {row[0] for row in connection.execute("SELECT grant_id FROM grants")} == {
        kept_grant_id,
        new_grant_id,
    }


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
        "https://example.test/api",
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
