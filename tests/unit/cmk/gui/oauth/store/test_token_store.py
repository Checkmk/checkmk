#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sqlite3
from datetime import datetime, timedelta, UTC

import pytest

from cmk.ccc.user import UserId
from cmk.gui.oauth.store.backend import create_schema
from cmk.gui.oauth.store.token_store import TokenRecord, TokenStore

_USER = UserId("cmkadmin")


@pytest.fixture
def store() -> TokenStore:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_schema(connection)
    return TokenStore(connection)


def _future(minutes: int) -> datetime:
    return (datetime.now(UTC) + timedelta(minutes=minutes)).replace(microsecond=0)


def _past(minutes: int) -> datetime:
    return (datetime.now(UTC) - timedelta(minutes=minutes)).replace(microsecond=0)


# TokenRecord.is_valid


def test_record_is_valid_before_it_expires() -> None:
    record = TokenRecord(
        user_id=_USER, issued_at=_past(5), expires_at=_future(5), resource=None, scope=None
    )

    assert record.is_valid(at=_future(1)) is True


def test_record_is_not_valid_after_it_expires() -> None:
    record = TokenRecord(
        user_id=_USER, issued_at=_past(10), expires_at=_past(5), resource=None, scope=None
    )

    assert record.is_valid(at=datetime.now(UTC)) is False


def test_record_is_valid_defaults_to_the_current_time() -> None:
    record = TokenRecord(
        user_id=_USER, issued_at=_past(5), expires_at=_future(60), resource=None, scope=None
    )

    assert record.is_valid() is True


def test_record_is_valid_rejects_naive_datetimes() -> None:
    record = TokenRecord(
        user_id=_USER, issued_at=_past(5), expires_at=_future(5), resource=None, scope=None
    )

    with pytest.raises(ValueError, match="timezone-aware"):
        record.is_valid(at=datetime.now())


# TokenStore.issue_token


def test_issue_token_stores_only_a_hash_never_the_plaintext(store: TokenStore) -> None:
    token = store.issue_token(_USER, expires_at=_future(60), resource=None, scope=None)

    stored_hashes = [row[0] for row in store._connection.execute("SELECT token_hash FROM tokens")]
    assert token not in stored_hashes


def test_issue_token_produces_unique_tokens(store: TokenStore) -> None:
    first = store.issue_token(_USER, expires_at=_future(60), resource=None, scope=None)
    second = store.issue_token(_USER, expires_at=_future(60), resource=None, scope=None)

    assert first != second


def test_issue_token_rejects_an_empty_user_id(store: TokenStore) -> None:
    with pytest.raises(ValueError, match="user_id"):
        store.issue_token(UserId(""), expires_at=_future(60), resource=None, scope=None)


def test_issue_token_rejects_an_expiry_in_the_past(store: TokenStore) -> None:
    with pytest.raises(ValueError, match="expires_at"):
        store.issue_token(_USER, expires_at=_past(5), resource=None, scope=None)


def test_issue_token_rejects_a_naive_expiry(store: TokenStore) -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        store.issue_token(
            _USER, expires_at=datetime.now() + timedelta(minutes=5), resource=None, scope=None
        )


# TokenStore.get_by_token


def test_get_by_token_returns_the_matching_record(store: TokenStore) -> None:
    expires_at = _future(60)

    token = store.issue_token(_USER, expires_at=expires_at, resource=None, scope=None)

    record = store.get_by_token(token)
    assert record is not None
    assert record.user_id == _USER
    assert record.expires_at == expires_at


def test_get_by_token_returns_none_for_an_unknown_token(store: TokenStore) -> None:
    assert store.get_by_token("never-issued") is None


def test_get_by_token_returns_the_bound_resource(store: TokenStore) -> None:
    token = store.issue_token(
        _USER, expires_at=_future(60), resource="https://host/mysite/check_mk/mcp", scope=None
    )

    record = store.get_by_token(token)
    assert record is not None
    assert record.resource == "https://host/mysite/check_mk/mcp"


def test_get_by_token_returns_none_for_an_unbound_resource(store: TokenStore) -> None:
    token = store.issue_token(_USER, expires_at=_future(60), resource=None, scope=None)

    record = store.get_by_token(token)
    assert record is not None
    assert record.resource is None


def test_get_by_token_returns_the_bound_scope(store: TokenStore) -> None:
    token = store.issue_token(_USER, expires_at=_future(60), resource=None, scope="mcp")

    record = store.get_by_token(token)
    assert record is not None
    assert record.scope == "mcp"


def test_get_by_token_returns_none_for_an_unbound_scope(store: TokenStore) -> None:
    token = store.issue_token(_USER, expires_at=_future(60), resource=None, scope=None)

    record = store.get_by_token(token)
    assert record is not None
    assert record.scope is None


# TokenStore.list_by_user


def test_list_by_user_returns_empty_for_a_user_without_tokens(store: TokenStore) -> None:
    assert store.list_by_user(_USER) == []


def test_list_by_user_only_returns_that_users_tokens(store: TokenStore) -> None:
    other_user = UserId("other")
    store.issue_token(other_user, expires_at=_future(60), resource=None, scope=None)
    store.issue_token(_USER, expires_at=_future(60), resource=None, scope=None)

    records = store.list_by_user(_USER)

    assert len(records) == 1
    assert records[0].user_id == _USER
