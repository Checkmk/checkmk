#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import sqlite3
from http import HTTPStatus
from pathlib import Path

import pytest

from cmk.gui.oauth.store import backend
from cmk.gui.oauth.store.backend import (
    connect,
    create_schema,
    open_connection,
    StoreUnavailableError,
)


@pytest.fixture(name="unseen_database")
def fixture_unseen_database(monkeypatch: pytest.MonkeyPatch) -> None:
    """Start out as a process that has not worked on any database yet."""
    monkeypatch.setattr(backend, "_known_identities", {})


def _insert_client(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT INTO clients (client_id, redirect_uris, client_name, registered_at)
        VALUES ('test-client', '[]', NULL, 0)
        """
    )


def _insert_token(connection: sqlite3.Connection) -> None:
    connection.execute(
        "INSERT INTO tokens (token_hash, user_id, issued_at, expires_at, client_id)"
        " VALUES (?, ?, ?, ?, ?)",
        ("a" * 64, "cmkadmin", 0, 100, "test-client"),
    )


def _tables(db_path: Path) -> set[str]:
    connection = sqlite3.connect(db_path)
    return {
        row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }


def _make_database(db_path: Path) -> None:
    """A separate, complete database, as a restore or a rebuild would leave behind."""
    with connect(db_path) as connection:
        _insert_client(connection)


def test_connect_creates_missing_parent_directories(tmp_path: Path) -> None:
    db_path = tmp_path / "nested" / "dir" / "db.sqlite3"

    with connect(db_path):
        pass

    assert db_path.exists()


def test_connect_creates_the_tokens_table(tmp_path: Path) -> None:
    db_path = tmp_path / "db.sqlite3"

    with connect(db_path):
        pass

    assert "tokens" in _tables(db_path)


def test_connect_preserves_data_written_by_an_earlier_connection(tmp_path: Path) -> None:
    db_path = tmp_path / "db.sqlite3"
    with connect(db_path) as connection:
        _insert_client(connection)
        _insert_token(connection)

    with connect(db_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM tokens").fetchone()[0] == 1


def test_connect_closes_the_connection_at_the_end_of_the_block(tmp_path: Path) -> None:
    with connect(tmp_path / "db.sqlite3") as connection:
        pass

    with pytest.raises(sqlite3.ProgrammingError, match="[Cc]losed database"):
        connection.execute("SELECT 1")


def test_connect_leaves_no_write_ahead_log_behind(tmp_path: Path) -> None:
    # A -wal left lying around is what makes replacing the database file
    # dangerous: sqlite replays it onto whatever file the path names next.
    db_path = tmp_path / "db.sqlite3"

    with connect(db_path) as connection:
        _insert_client(connection)

    assert [path.name for path in tmp_path.iterdir()] == ["db.sqlite3"]


def test_connect_uses_the_database_the_path_currently_names(tmp_path: Path) -> None:
    db_path = tmp_path / "db.sqlite3"
    replacement = tmp_path / "restored.sqlite3"
    _make_database(db_path)
    _make_database(replacement)
    with connect(replacement) as connection:
        connection.execute(
            "UPDATE clients SET client_name = 'from the replacement' WHERE client_id = ?",
            ("test-client",),
        )
    replacement.replace(db_path)

    with connect(db_path) as connection:
        name = connection.execute("SELECT client_name FROM clients").fetchone()["client_name"]

    assert name == "from the replacement"


def test_connect_recreates_a_deleted_database(tmp_path: Path) -> None:
    db_path = tmp_path / "db.sqlite3"
    with connect(db_path) as connection:
        _insert_client(connection)
    db_path.unlink()

    with connect(db_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM clients").fetchone()[0] == 0


@pytest.mark.usefixtures("unseen_database")
def test_connect_is_quiet_about_a_database_it_creates(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger="cmk.web"), connect(tmp_path / "db.sqlite3"):
        pass

    assert not caplog.records


@pytest.mark.usefixtures("unseen_database")
def test_connect_reports_a_replaced_database(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    db_path = tmp_path / "db.sqlite3"
    replacement = tmp_path / "restored.sqlite3"
    _make_database(db_path)
    _make_database(replacement)
    replacement.replace(db_path)

    with caplog.at_level(logging.WARNING, logger="cmk.web"), connect(db_path):
        pass

    assert "was replaced while the site was running" in caplog.text


@pytest.mark.usefixtures("unseen_database")
def test_connect_reports_a_deleted_database(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    db_path = tmp_path / "db.sqlite3"
    _make_database(db_path)
    db_path.unlink()

    with caplog.at_level(logging.WARNING, logger="cmk.web"), connect(db_path):
        pass

    assert "has been re-created empty" in caplog.text
    assert caplog.records[0].levelno == logging.ERROR


def test_connect_rejects_a_database_from_an_unsupported_schema_version(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    db_path = tmp_path / "db.sqlite3"
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA user_version=5")
    connection.close()

    with (
        caplog.at_level(logging.ERROR, logger="cmk.web"),
        pytest.raises(StoreUnavailableError),
        connect(db_path),
    ):
        pass

    assert "schema version 5" in caplog.text


def test_an_unavailable_store_is_a_service_unavailable_response() -> None:
    # No page catches StoreUnavailableError: both WSGI applications answer an
    # MKHTTPException with its status, which is what keeps an unusable
    # database from becoming a crash report per request.
    assert StoreUnavailableError("").status == HTTPStatus.SERVICE_UNAVAILABLE


def test_connect_reports_a_damaged_database_as_unavailable(tmp_path: Path) -> None:
    db_path = tmp_path / "db.sqlite3"
    _make_database(db_path)
    with db_path.open("r+b") as damaged:
        damaged.seek(100)
        damaged.write(b"\x00" * 4096)

    with pytest.raises(StoreUnavailableError) as raised, connect(db_path) as connection:
        connection.execute("SELECT COUNT(*) FROM clients").fetchone()

    # The message reaches unauthenticated clients, so the path and the sqlite
    # error belong in the log instead.
    assert str(db_path) not in str(raised.value)


def test_connect_reports_an_unwritable_location_as_unavailable(tmp_path: Path) -> None:
    not_a_directory = tmp_path / "file"
    not_a_directory.touch()

    with pytest.raises(StoreUnavailableError), connect(not_a_directory / "db.sqlite3"):
        pass


def test_create_schema_sets_the_schema_version() -> None:
    connection = sqlite3.connect(":memory:")

    create_schema(connection)

    assert connection.execute("PRAGMA user_version").fetchone()[0] == 4


def test_create_schema_rejects_a_newer_schema_version() -> None:
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA user_version=5")

    with pytest.raises(StoreUnavailableError):
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

    with pytest.raises(StoreUnavailableError):
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
    with connect(db_path):
        pass
    connection = open_connection(db_path)
    _insert_client(connection)
    _insert_token(connection)

    row = connection.execute("SELECT * FROM tokens").fetchone()

    assert row["user_id"] == "cmkadmin"
