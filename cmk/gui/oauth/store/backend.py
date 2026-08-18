#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from http import HTTPStatus
from pathlib import Path

import cmk.utils.paths
from cmk.gui.exceptions import MKHTTPException
from cmk.gui.log import logger

SCHEMA_VERSION = 4

# Changing a table that already exists needs SCHEMA_VERSION bumped: create_schema
# replays these statements on existing databases, where the CREATE is a no-op.
# clients comes first because tokens references it.
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS clients (
    client_id TEXT PRIMARY KEY NOT NULL CHECK (client_id <> ''),
    redirect_uris TEXT NOT NULL,
    client_name TEXT,
    registered_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS tokens (
    token_hash TEXT PRIMARY KEY NOT NULL CHECK (length(token_hash) = 64),
    user_id TEXT NOT NULL CHECK (user_id <> ''),
    issued_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,
    resource TEXT,
    scope TEXT,
    client_id TEXT NOT NULL CHECK (client_id <> '')
        REFERENCES clients(client_id) ON DELETE CASCADE,
    CHECK (expires_at > issued_at)
);

CREATE INDEX IF NOT EXISTS idx_tokens_user_id_issued_at
    ON tokens (user_id, issued_at DESC);

CREATE INDEX IF NOT EXISTS idx_tokens_expires_at
    ON tokens (expires_at);

-- Deleting a client cascades into tokens. Without this index that is a
-- full-table scan per deleted client.
CREATE INDEX IF NOT EXISTS idx_tokens_client_id
    ON tokens (client_id);
"""
SCHEMA_STATEMENTS = [statement.strip() for statement in SCHEMA_SQL.split(";") if statement.strip()]


class StoreUnavailableError(MKHTTPException):
    """The OAuth database cannot be opened, or is not one we can work with.

    Only cmk.gui.oauth.find_access_token catches this; everywhere else both
    WSGI applications answer an MKHTTPException with its status, so an
    unusable database costs a 503 per request instead of a crash report.
    Whoever raises it logs the reason -- the message here also reaches
    unauthenticated clients.
    """

    status = HTTPStatus.SERVICE_UNAVAILABLE  # type: ignore[mutable-override]


_UNAVAILABLE = "The OAuth database is unavailable. See var/log/web.log for details."


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

    Exposed separately from connect() so callers that already hold a
    connection to a database that only exists for as long as that connection
    stays open (e.g. an in-memory sqlite database in tests) can initialize it
    in place.
    """
    with write_transaction(connection):
        current_version = _get_schema_version(connection)
        if current_version not in (0, SCHEMA_VERSION):
            logger.error(
                "The OAuth database has schema version %(current)d, expected %(expected)d",
                {"current": current_version, "expected": SCHEMA_VERSION},
            )
            raise StoreUnavailableError(_UNAVAILABLE)

        for statement in SCHEMA_STATEMENTS:
            connection.execute(statement)

        if current_version == 0:
            connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")


def open_connection(db_path: str | Path, *, timeout_seconds: float = 30.0) -> sqlite3.Connection:
    """Open a connection to db_path, without touching the schema.

    Prefer connect(), which also creates the schema when needed and closes the
    connection again; this is for callers that manage both themselves.
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


def _ensure_schema(connection: sqlite3.Connection) -> None:
    """Bring a freshly opened database up to the current schema.

    Runs on every connection, hence the version check first: reading
    user_version takes no lock, while create_schema's BEGIN IMMEDIATE would
    serialize every request behind a write lock. Two processes racing here is
    harmless -- create_schema re-reads the version inside its transaction.
    """
    if _get_schema_version(connection) == SCHEMA_VERSION:
        return

    if connection.execute("PRAGMA journal_mode").fetchone()[0] != "wal":
        # Switching journal mode takes an exclusive lock, and WAL is a property
        # of the file, so this is only for a database we are creating.
        connection.execute("PRAGMA journal_mode=WAL")

    create_schema(connection)


# The identity of the database file this process last worked on, so that it can
# tell "somebody swapped the file" apart from business as usual. Keyed by path,
# so a process working on more than one database (tests, mainly) does not report
# every switch between them as a replacement.
_identity_lock = threading.Lock()
_known_identities: dict[Path, tuple[int, int]] = {}


def _warn_if_file_changed(db_path: Path, *, was_missing: bool) -> None:
    """Log when the file we just opened is not the one this process used before.

    Requests recover on their own, so without this the only symptom of an
    admin swapping the file would be every OAuth client having to register
    again. Deletion is recognized by the file having been missing rather than
    by its identity, because a re-created file usually gets the freed inode
    back. An overwrite in place keeps the inode and is indistinguishable from
    our own writes; that one shows up as a damaged database instead.
    """
    try:
        stat = db_path.stat()
    except OSError:
        return

    identity = (stat.st_dev, stat.st_ino)
    with _identity_lock:
        previously_known = _known_identities.get(db_path)
        _known_identities[db_path] = identity

    if previously_known is None:
        return

    if was_missing:
        logger.error(
            "The OAuth database %(path)s was deleted while the site was running and has been "
            "re-created empty: all registered OAuth clients and issued access tokens are gone, "
            "and clients have to register again. Removing or replacing this file requires a "
            "stopped site.",
            {"path": db_path},
        )
    elif previously_known != identity:
        logger.warning(
            "The OAuth database %(path)s was replaced while the site was running. Requests from "
            "now on use the new file, but replacing it under a running site can corrupt it -- "
            "do this with the site stopped.",
            {"path": db_path},
        )


@contextmanager
def connect(db_path: Path) -> Iterator[sqlite3.Connection]:
    """Open a connection for one unit of work, and close it again afterwards.

    Deliberately short-lived: a connection held open keeps the file it was
    opened on, so once that file is deleted or replaced its reads and writes
    silently go to a database nobody else can see. Reconnecting costs a
    fraction of a millisecond and keeps every request on the file the path
    currently names.
    """
    was_missing = not db_path.exists()
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = open_connection(db_path)
    except (OSError, sqlite3.Error) as e:
        logger.exception("Cannot open the OAuth database %(path)s", {"path": db_path})
        raise StoreUnavailableError(_UNAVAILABLE) from e

    try:
        _warn_if_file_changed(db_path, was_missing=was_missing)
        _ensure_schema(connection)
        yield connection
    except sqlite3.Error as e:
        # Also covers a database damaged by being swapped out mid-write
        # ("database disk image is malformed"). Failures a store handles
        # itself (see TokenStore.issue_token) never get here.
        logger.exception("Cannot use the OAuth database %(path)s", {"path": db_path})
        raise StoreUnavailableError(_UNAVAILABLE) from e
    finally:
        connection.close()


class Backend:
    """Shared sqlite plumbing for the OAuth stores.

    A store does not own its connection: connect() closes it at the end of the
    with block each store's accessor hands it out for. A store must not
    outlive that block.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def write_transaction(self) -> AbstractContextManager[None]:
        return write_transaction(self._connection)


def oauth_db_path() -> Path:
    return cmk.utils.paths.var_dir / "oauth" / "db.sqlite3"
