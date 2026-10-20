#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The SQLite `Backend`.

Records the id of the last applied revision as the only row of
`REVISION_TABLE`, like alembic, and applies each revision in its own
transaction so a crash mid-revision rolls back cleanly.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
from collections import Counter
from collections.abc import Callable, Generator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from logging import Logger
from pathlib import Path
from sqlite3 import Connection
from typing import override
from urllib.parse import quote

from cmk.schema_manager._discovery import discover_db_migrations
from cmk.schema_manager._mechanism import ensure_schema, ensure_schemas_on_update
from cmk.schema_manager._paths import db_path, site_relative_db_path
from cmk.schema_manager.backend.base import Backend
from cmk.schema_manager.errors import (
    BackendUnavailableError,
    ForeignKeyViolationError,
    SchemaVersionAheadError,
)
from cmk.schema_manager.revision import RevisionChain

REVISION_TABLE = "_cmk_schema_revision"

# Shared by every adopter so the settings cannot drift apart.
CONNECTION_PRAGMAS: Sequence[str] = (
    "PRAGMA foreign_keys=ON",
    "PRAGMA synchronous=NORMAL",
    "PRAGMA journal_mode=WAL",
)


_LOGGER = logging.getLogger(__name__)


def apply_connection_pragmas(connection: Connection) -> None:
    for pragma in CONNECTION_PRAGMAS:
        connection.execute(pragma)
    # SQLite silently keeps another mode where WAL is unsupported, e.g. on
    # some network filesystems. In-memory databases always report "memory".
    journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
    if journal_mode not in ("wal", "memory"):
        _LOGGER.warning(
            "The database runs in journal mode %(mode)s instead of WAL; "
            "its filesystem may not support WAL",
            {"mode": journal_mode},
        )


# Identity of each database file last connected to, keyed by path, so a
# repeat connection can tell "somebody swapped the file" apart from normal use.
_identity_lock = threading.Lock()
_known_identities: dict[Path, tuple[int, int]] = {}


def _warn_if_file_replaced(path: Path) -> None:
    try:
        stat = path.stat()
    except OSError:
        return

    identity = (stat.st_dev, stat.st_ino)
    with _identity_lock:
        previously_known = _known_identities.get(path)
        _known_identities[path] = identity

    if previously_known is not None and previously_known != identity:
        _LOGGER.warning(
            "The database at %(path)s was replaced while in use. Connections from now on "
            "use the new file, but replacing it under a running process can corrupt it -- "
            "do this with the process stopped.",
            {"path": path},
        )


@contextmanager
def write_transaction(connection: Connection) -> Generator[None]:
    """Run a block of statements atomically, rolling back on any exception."""
    connection.execute("BEGIN IMMEDIATE")
    try:
        yield
        connection.execute("COMMIT")
    except Exception:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        raise


@dataclass(frozen=True)
class Sqlite(Backend[Connection]):
    """One file per database name: var/check_mk/<name>/db.sqlite3.

    Connections use `sqlite3.Row`; `configure` runs on each new connection
    and applies `CONNECTION_PRAGMAS` unless overridden. `busy_timeout` is
    how many seconds a connection waits for a lock held by another one.

    Revisions run with foreign keys off, so one can rebuild a table. If
    they were on, a revision that adds violating rows fails before it
    commits.
    """

    configure: Callable[[Connection], None] = apply_connection_pragmas
    busy_timeout: float = 30.0

    def path(self, name: str) -> Path:
        return db_path(name)

    def site_relative_path(self, name: str) -> Path:
        """`path` relative to the site's home directory."""
        return site_relative_db_path(name)

    @override
    @contextmanager
    def connect(self, name: str, *, create: bool = False) -> Generator[Connection]:
        """Short-lived, so a replaced file is always reopened.

        Failing to open, including a missing database unless `create` is
        set, raises `BackendUnavailableError`.
        """
        path = self.path(name)
        try:
            connection = self._open(path, create=create)
        except (OSError, sqlite3.Error) as e:
            _LOGGER.exception("Cannot open the database at %(path)s", {"path": path})
            raise BackendUnavailableError(str(path)) from e
        try:
            _warn_if_file_replaced(path)
            yield connection
        finally:
            connection.close()

    def _open(self, path: Path, *, create: bool) -> Connection:
        if create:
            path.parent.mkdir(parents=True, exist_ok=True)
        mode = "rwc" if create else "rw"
        connection = sqlite3.connect(
            f"file:{quote(str(path))}?mode={mode}",
            uri=True,
            # The sqlite3 module then never begins or commits a transaction
            # itself: a statement outside BEGIN ... COMMIT commits on its own,
            # as in plain SQLite, and transactions are exactly the ones the
            # code opens with BEGIN and ends with COMMIT or ROLLBACK
            # statements. commit() and rollback() do nothing in this mode.
            # autocommit=False would keep a transaction open at all times,
            # so writers could not take the lock up front with BEGIN
            # IMMEDIATE, and the pragmas could not be switched.
            autocommit=True,
            timeout=self.busy_timeout,
        )
        connection.row_factory = sqlite3.Row
        try:
            self.configure(connection)
        except Exception:
            connection.close()
            raise
        return connection

    @override
    def exists(self, name: str) -> bool:
        return self.path(name).exists()

    @override
    def apply_pending(
        self, context: Connection, chain: RevisionChain[Connection], logger: Logger
    ) -> None:
        if context.autocommit is not True:
            # In the other modes the sqlite3 module manages transactions
            # itself, e.g. executescript() commits what a revision did before
            # it, and the revision is no longer atomic.
            raise ValueError("apply_pending needs a connection opened with autocommit=True")
        context.execute(f"CREATE TABLE IF NOT EXISTS {REVISION_TABLE} (id TEXT NOT NULL)")
        chain_ids = [revision.id for revision in chain]
        current = _current_position(context, chain_ids)

        for position, revision in enumerate(chain.revisions[current + 1 :], start=current + 1):
            with _foreign_keys_off(context) as foreign_keys_on, write_transaction(context):
                # Another process may have applied it since the read above.
                if _current_position(context, chain_ids) >= position:
                    continue
                logger.info(
                    "Applying schema revision %(revision_id)s", {"revision_id": revision.id}
                )
                violations_before = _foreign_key_violations(context) if foreign_keys_on else None
                revision.upgrade(context)
                if violations_before is not None:
                    _check_no_new_foreign_key_violations(context, revision.id, violations_before)
                context.execute(f"DELETE FROM {REVISION_TABLE}")  # nosec B608 # BNS:fa3c6c
                context.execute(
                    f"INSERT INTO {REVISION_TABLE} (id) VALUES (?)",  # nosec B608 # BNS:fa3c6c
                    (revision.id,),
                )


class SqliteInMemory(Sqlite):
    """In-memory `Sqlite`. Each `connect()` gets a fresh, empty database."""

    @override
    def path(self, name: str) -> Path:
        return Path(":memory:")


def _current_position(connection: Connection, chain_ids: Sequence[str]) -> int:
    """-1 for a database no revision was applied to yet."""
    row = connection.execute(
        f"SELECT id FROM {REVISION_TABLE}"  # nosec B608 # BNS:fa3c6c
    ).fetchone()
    if row is None:
        return -1
    if row[0] not in chain_ids:
        raise SchemaVersionAheadError(row[0])
    return chain_ids.index(row[0])


@contextmanager
def _foreign_keys_off(connection: Connection) -> Generator[bool]:
    """Yields whether foreign keys were on before.

    SQLite's procedure for rebuilding a table: with foreign keys on,
    dropping the old table runs ON DELETE actions on the rows that
    reference it. The pragma is ignored inside a transaction, so it is
    switched here, around it.
    """
    if not connection.execute("PRAGMA foreign_keys").fetchone()[0]:
        yield False
        return
    connection.execute("PRAGMA foreign_keys=OFF")
    try:
        yield True
    finally:
        connection.execute("PRAGMA foreign_keys=ON")


def _foreign_key_violations(connection: Connection) -> Counter[tuple[str, str]]:
    """Violations per (table, parent table), not per row: rebuilding a
    table can change the rowids of rows that already violated a key."""
    return Counter((row[0], row[2]) for row in connection.execute("PRAGMA foreign_key_check"))


def _check_no_new_foreign_key_violations(
    connection: Connection, revision_id: str, before: Counter[tuple[str, str]]
) -> None:
    # Rows that already violated a key, e.g. written with foreign keys
    # off, must not fail every later revision.
    if introduced := _foreign_key_violations(connection) - before:
        raise ForeignKeyViolationError(revision_id, sorted(introduced))


def ensure_sqlite_up_to_date(logger: Logger) -> None:
    """The `omd update` hook: apply pending revisions to every SQLite
    database opted into "update"."""
    ensure_schemas_on_update(
        discover_db_migrations(backend_type=Sqlite, event="update").values(), logger
    )


def ensure_sqlite_created(logger: Logger) -> None:
    """The `omd create` hook: create every SQLite database opted into
    "create" and apply its pending revisions."""
    for database in discover_db_migrations(backend_type=Sqlite, event="create").values():
        ensure_schema(database, logger)


def sqlite_backup_paths() -> list[Path]:
    """Site-relative paths of every SQLite database opted into "backup",
    for `omd backup` to snapshot.

    A broken plugin must not prevent the backup: then no path is returned,
    and the databases are archived as plain files.
    """
    try:
        databases = discover_db_migrations(backend_type=Sqlite, event="backup").values()
    except Exception as e:
        _LOGGER.warning(
            "Failed to discover the schema-manager databases (%(error)s). "
            "They are archived as plain files instead of snapshots.",
            {"error": e},
        )
        return []
    return [database.backend.site_relative_path(database.name) for database in databases]
