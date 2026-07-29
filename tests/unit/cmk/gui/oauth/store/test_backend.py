#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sqlite3
from pathlib import Path

import pytest

from cmk.gui.oauth.store.backend import create_schema, initialize_database, open_connection


def _insert_client(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT INTO clients (client_id, redirect_uris, client_name, registered_at)
        VALUES ('test-client', '[]', NULL, 0)
        """
    )


def _tables(db_path: Path) -> set[str]:
    connection = sqlite3.connect(db_path)
    return {
        row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }


def test_initialize_database_creates_missing_parent_directories(tmp_path: Path) -> None:
    db_path = tmp_path / "nested" / "dir" / "db.sqlite3"

    initialize_database(db_path)

    assert db_path.exists()


def test_initialize_database_creates_the_tokens_table(tmp_path: Path) -> None:
    db_path = tmp_path / "db.sqlite3"

    initialize_database(db_path)

    assert "tokens" in _tables(db_path)


def test_initialize_database_is_idempotent_and_preserves_data(tmp_path: Path) -> None:
    db_path = tmp_path / "db.sqlite3"
    initialize_database(db_path)
    connection = sqlite3.connect(db_path)
    _insert_client(connection)
    connection.execute(
        "INSERT INTO tokens (token_hash, user_id, issued_at, expires_at, client_id)"
        " VALUES (?, ?, ?, ?, ?)",
        ("a" * 64, "cmkadmin", 0, 100, "test-client"),
    )
    connection.commit()
    connection.close()

    initialize_database(db_path)

    connection = sqlite3.connect(db_path)
    assert connection.execute("SELECT COUNT(*) FROM tokens").fetchone()[0] == 1


def test_create_schema_sets_the_schema_version() -> None:
    connection = sqlite3.connect(":memory:")

    create_schema(connection)

    assert connection.execute("PRAGMA user_version").fetchone()[0] == 4


def test_create_schema_rejects_a_newer_schema_version() -> None:
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA user_version=5")

    with pytest.raises(RuntimeError, match="unsupported schema version"):
        create_schema(connection)


@pytest.mark.parametrize("earlier_version", [1, 2, 3])
def test_create_schema_rejects_a_database_from_an_earlier_schema_version(
    earlier_version: int,
) -> None:
    # The point of bumping SCHEMA_VERSION: a database created before a column
    # was added cannot be repaired by replaying CREATE TABLE IF NOT EXISTS, so
    # it has to fail loudly here instead of silently missing the column.
    connection = sqlite3.connect(":memory:")
    connection.execute(f"PRAGMA user_version={earlier_version}")

    with pytest.raises(RuntimeError, match="unsupported schema version"):
        create_schema(connection)


def test_tokens_table_rejects_a_token_hash_of_the_wrong_length() -> None:
    connection = sqlite3.connect(":memory:")
    create_schema(connection)

    _insert_client(connection)

    with pytest.raises(sqlite3.IntegrityError, match="length\\(token_hash\\) = 64"):
        connection.execute(
            "INSERT INTO tokens (token_hash, user_id, issued_at, expires_at, client_id)"
            " VALUES (?, ?, ?, ?, ?)",
            ("too-short", "cmkadmin", 0, 100, "test-client"),
        )


def test_tokens_table_rejects_expires_at_not_after_issued_at() -> None:
    connection = sqlite3.connect(":memory:")
    create_schema(connection)

    _insert_client(connection)

    with pytest.raises(sqlite3.IntegrityError, match="expires_at > issued_at"):
        connection.execute(
            "INSERT INTO tokens (token_hash, user_id, issued_at, expires_at, client_id)"
            " VALUES (?, ?, ?, ?, ?)",
            ("a" * 64, "cmkadmin", 100, 100, "test-client"),
        )


def test_open_connection_returns_rows_addressable_by_column_name(tmp_path: Path) -> None:
    db_path = tmp_path / "db.sqlite3"
    initialize_database(db_path)
    connection = open_connection(db_path)
    _insert_client(connection)
    connection.execute(
        "INSERT INTO tokens (token_hash, user_id, issued_at, expires_at, client_id)"
        " VALUES (?, ?, ?, ?, ?)",
        ("a" * 64, "cmkadmin", 0, 100, "test-client"),
    )

    row = connection.execute("SELECT * FROM tokens").fetchone()

    assert row["user_id"] == "cmkadmin"
