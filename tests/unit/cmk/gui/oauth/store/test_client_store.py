#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sqlite3

import pytest

from cmk.gui.oauth.store.backend import create_schema
from cmk.gui.oauth.store.client_store import ClientRegistrationLimitExceededError, ClientStore


@pytest.fixture
def store() -> ClientStore:
    connection = sqlite3.connect(":memory:", isolation_level=None)
    connection.row_factory = sqlite3.Row
    create_schema(connection)
    return ClientStore(connection)


def _seed_clients(store: ClientStore, n: int) -> None:
    store._connection.executemany(
        """
        INSERT INTO clients (client_id, redirect_uris, client_name, registered_at)
        VALUES (?, '["https://client.example/callback"]', NULL, 0)
        """,
        [(f"client-{i}",) for i in range(n)],
    )


def test_register_then_get_returns_it(store: ClientStore) -> None:
    registered = store.register(["https://client.example/callback"], "Example")

    assert store.get(registered.client_id) == registered


def test_two_registered_clients_are_both_retrievable(store: ClientStore) -> None:
    first = store.register(["https://client.example/first"], "First Client")
    second = store.register(["https://client.example/second"], "Second Client")

    assert store.get(first.client_id) == first
    assert store.get(second.client_id) == second
    assert first != second


def test_get_returns_none_for_an_unknown_client_id(store: ClientStore) -> None:
    assert store.get("does-not-exist") is None


def test_register_raises_when_store_is_at_capacity(store: ClientStore) -> None:
    _seed_clients(store, 1000)

    with pytest.raises(ClientRegistrationLimitExceededError):
        store.register(["https://client.example/callback"], "Example")


def test_register_does_not_add_a_row_when_store_is_at_capacity(store: ClientStore) -> None:
    _seed_clients(store, 1000)

    with pytest.raises(ClientRegistrationLimitExceededError):
        store.register(["https://client.example/callback"], "Example")

    count = store._connection.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
    assert count == 1000


def test_register_succeeds_when_store_is_one_below_capacity(store: ClientStore) -> None:
    _seed_clients(store, 999)

    registered = store.register(["https://client.example/callback"], "Example")

    assert store.get(registered.client_id) == registered


# ClientStore.list


def test_list_returns_empty_list_when_store_is_empty(store: ClientStore) -> None:
    assert store.list() == []


def test_list_returns_all_clients_sorted_by_registered_at_ascending(store: ClientStore) -> None:
    store._connection.executemany(
        """
        INSERT INTO clients (client_id, redirect_uris, client_name, registered_at)
        VALUES (?, '["https://client.example/callback"]', NULL, ?)
        """,
        [("newest", 300), ("oldest", 100), ("middle", 200)],
    )

    assert [client.client_id for client in store.list()] == ["oldest", "middle", "newest"]


# ClientStore.delete


def test_delete_removes_single_client_and_returns_count(store: ClientStore) -> None:
    registered = store.register(["https://client.example/callback"], "Example")

    assert store.delete([registered.client_id]) == 1
    assert store.get(registered.client_id) is None


def test_delete_removes_multiple_clients_and_returns_count(store: ClientStore) -> None:
    first = store.register(["https://client.example/first"], "First Client")
    second = store.register(["https://client.example/second"], "Second Client")

    assert store.delete([first.client_id, second.client_id]) == 2
    assert store.get(first.client_id) is None
    assert store.get(second.client_id) is None


def test_delete_ignores_unknown_client_id_mixed_in(store: ClientStore) -> None:
    registered = store.register(["https://client.example/callback"], "Example")

    assert store.delete([registered.client_id, "does-not-exist"]) == 1
    assert store.get(registered.client_id) is None


def test_delete_with_empty_collection_is_a_noop(store: ClientStore) -> None:
    registered = store.register(["https://client.example/callback"], "Example")

    assert store.delete([]) == 0
    assert store.get(registered.client_id) == registered


def test_delete_dedupes_duplicate_ids_in_input(store: ClientStore) -> None:
    registered = store.register(["https://client.example/callback"], "Example")

    assert store.delete([registered.client_id, registered.client_id]) == 1


def test_delete_on_empty_store_returns_zero(store: ClientStore) -> None:
    assert store.delete(["does-not-exist"]) == 0
