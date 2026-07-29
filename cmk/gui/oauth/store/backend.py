#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path

import cmk.utils.paths

SCHEMA_VERSION = 3

# Changing a table that already exists needs SCHEMA_VERSION bumped: create_schema
# replays these statements on existing databases, where the CREATE is a no-op.
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS tokens (
    token_hash TEXT PRIMARY KEY NOT NULL CHECK (length(token_hash) = 64),
    user_id TEXT NOT NULL CHECK (user_id <> ''),
    issued_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,
    resource TEXT,
    scope TEXT,
    CHECK (expires_at > issued_at)
);

CREATE INDEX IF NOT EXISTS idx_tokens_user_id_issued_at
    ON tokens (user_id, issued_at DESC);

CREATE INDEX IF NOT EXISTS idx_tokens_expires_at
    ON tokens (expires_at);

CREATE TABLE IF NOT EXISTS clients (
    client_id TEXT PRIMARY KEY NOT NULL CHECK (client_id <> ''),
    redirect_uris TEXT NOT NULL,
    client_name TEXT,
    registered_at INTEGER NOT NULL
);
"""
SCHEMA_STATEMENTS = [statement.strip() for statement in SCHEMA_SQL.split(";") if statement.strip()]


def _get_schema_version(connection: sqlite3.Connection) -> int:
    return int(connection.execute("PRAGMA user_version").fetchone()[0])


@contextmanager
def write_transaction(connection: sqlite3.Connection) -> Iterator[None]:
    """Run a block of statements atomically, rolling back on any exception.

    Needed for multi-statement check-then-write operations on a connection
    opened in autocommit mode (isolation_level=None, see open_connection) --
    a single execute() there already commits on its own.
    """
    connection.execute("BEGIN IMMEDIATE")
    try:
        yield
        connection.commit()
    except Exception:
        if connection.in_transaction:
            connection.rollback()
        raise


def create_schema(connection: sqlite3.Connection) -> None:
    """Create the schema (if needed) on an already-open connection.

    Exposed separately from initialize_database so callers that already hold
    a connection to a database that only exists for as long as that
    connection stays open (e.g. an in-memory sqlite database in tests) can
    initialize it in place, without going through a second, short-lived
    connection that would just discard the schema again on close.
    """
    with write_transaction(connection):
        current_version = _get_schema_version(connection)
        if current_version not in (0, SCHEMA_VERSION):
            raise RuntimeError(
                f"unsupported schema version {current_version}; expected {SCHEMA_VERSION}"
            )

        for statement in SCHEMA_STATEMENTS:
            connection.execute(statement)

        if current_version == 0:
            connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")


def initialize_database(db_path: str | Path) -> None:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path, timeout=30.0)
    try:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA temp_store=MEMORY")
        create_schema(connection)
    finally:
        connection.close()


def open_connection(db_path: str | Path, *, timeout_seconds: float = 30.0) -> sqlite3.Connection:
    """Open a connection to db_path; call initialize_database first if the
    schema might not exist yet.

    check_same_thread is disabled so the returned connection can be shared as
    a process-wide singleton across the (possibly multi-threaded) GUI worker,
    instead of every request opening and closing its own connection.
    """
    connection = sqlite3.connect(
        db_path,
        timeout=timeout_seconds,
        isolation_level=None,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout=30000")
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA synchronous=NORMAL")
    return connection


class Backend:
    """Shared sqlite plumbing for the OAuth stores.

    A store does not own its connection -- the accessors in cmk.gui.oauth hand
    out a fresh one per request around the process-wide connection. Hence no
    close(): it would take OAuth down for the rest of that process's life.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def write_transaction(self) -> AbstractContextManager[None]:
        return write_transaction(self._connection)


def oauth_db_path() -> Path:
    return cmk.utils.paths.var_dir / "oauth" / "db.sqlite3"
