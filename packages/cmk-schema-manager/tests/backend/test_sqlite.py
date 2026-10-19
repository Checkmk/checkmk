#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import sqlite3
from collections.abc import Callable, Iterator
from contextlib import closing
from pathlib import Path

import pytest

from cmk.schema_manager.backend import sqlite as sqlite_backend
from cmk.schema_manager.backend.sqlite import (
    apply_connection_pragmas,
    REVISION_TABLE,
    Sqlite,
    SqliteInMemory,
    write_transaction,
)
from cmk.schema_manager.errors import (
    BackendUnavailableError,
    ForeignKeyViolationError,
    SchemaVersionAheadError,
)
from cmk.schema_manager.revision import RevisionChain
from cmk.testlib.schema_manager import FakeRevision

_LOGGER = logging.getLogger("test")


@pytest.fixture(name="unseen_database")
def fixture_unseen_database(monkeypatch: pytest.MonkeyPatch) -> None:
    """Start out as a process that has not connected to any database yet."""
    monkeypatch.setattr(sqlite_backend, "_known_identities", {})


def _make_database(path: Path, value: int = 1) -> None:
    """A database with one table and one row."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path, isolation_level=None)) as connection:
        connection.execute("CREATE TABLE t (x INTEGER)")
        connection.execute("INSERT INTO t VALUES (?)", (value,))


@pytest.mark.usefixtures("omd_root")
def test_exists_is_false_when_the_file_is_absent() -> None:
    assert Sqlite().exists("db") is False


@pytest.mark.usefixtures("omd_root")
def test_exists_is_true_when_the_file_is_present() -> None:
    db_path = Sqlite().path("db")
    db_path.parent.mkdir(parents=True)
    db_path.touch()

    assert Sqlite().exists("db") is True


@pytest.mark.usefixtures("omd_root")
def test_connect_runs_configure_on_the_new_connection() -> None:
    configured: list[sqlite3.Connection] = []
    backend = Sqlite(configure=configured.append)

    with backend.connect("db", create=True) as connection:
        assert configured == [connection]


@pytest.mark.usefixtures("omd_root")
def test_connect_sets_row_factory_regardless_of_configure() -> None:
    backend = Sqlite(configure=lambda _: None)

    with backend.connect("db", create=True) as connection:
        connection.execute("CREATE TABLE t (id INTEGER)")
        connection.execute("INSERT INTO t (id) VALUES (1)")
        row = connection.execute("SELECT id FROM t").fetchone()
        assert row["id"] == 1


def test_in_memory_opens_a_usable_connection() -> None:
    with SqliteInMemory().connect("db") as connection:
        connection.execute("CREATE TABLE t (id INTEGER)")
        connection.execute("INSERT INTO t (id) VALUES (1)")
        assert [row["id"] for row in connection.execute("SELECT id FROM t")] == [1]


def test_in_memory_runs_configure_on_the_new_connection() -> None:
    configured: list[sqlite3.Connection] = []

    with SqliteInMemory(configure=configured.append).connect("db") as connection:
        assert configured == [connection]


def test_in_memory_does_not_touch_the_filesystem(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    with SqliteInMemory().connect("db"):
        pass

    assert list(tmp_path.iterdir()) == []


def test_path_resolves_the_name_under_var_check_mk_at_call_time(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backend = Sqlite()
    monkeypatch.setenv("OMD_ROOT", str(tmp_path))

    assert backend.path("oauth") == tmp_path / "var" / "check_mk" / "oauth" / "db.sqlite3"


@pytest.fixture(name="connection")
def fixture_connection() -> Iterator[sqlite3.Connection]:
    with SqliteInMemory().connect("db") as connection:
        yield connection


def test_apply_pending_applies_every_revision_in_order(connection: sqlite3.Connection) -> None:
    applied: list[str] = []
    chain: RevisionChain[sqlite3.Connection] = RevisionChain(
        (
            FakeRevision("0001", lambda _: applied.append("0001")),
            FakeRevision("0002", lambda _: applied.append("0002")),
        )
    )

    Sqlite().apply_pending(connection, chain, _LOGGER)

    assert applied == ["0001", "0002"]


def test_apply_pending_records_only_the_last_applied_revision(
    connection: sqlite3.Connection,
) -> None:
    chain: RevisionChain[sqlite3.Connection] = RevisionChain(
        (FakeRevision("0001"), FakeRevision("0002"))
    )

    Sqlite().apply_pending(connection, chain, _LOGGER)

    assert _recorded_revisions(connection) == ["0002"]


def test_apply_pending_is_a_noop_once_everything_is_applied(connection: sqlite3.Connection) -> None:
    calls: list[str] = []
    chain: RevisionChain[sqlite3.Connection] = RevisionChain(
        (FakeRevision("0001", lambda _: calls.append("0001")),)
    )
    backend = Sqlite()

    backend.apply_pending(connection, chain, _LOGGER)
    backend.apply_pending(connection, chain, _LOGGER)

    assert calls == ["0001"]


def test_apply_pending_raises_when_database_recorded_an_id_unknown_to_the_chain(
    connection: sqlite3.Connection,
) -> None:
    connection.execute(f"CREATE TABLE {REVISION_TABLE} (id TEXT NOT NULL)")
    connection.execute(f"INSERT INTO {REVISION_TABLE} (id) VALUES ('9999')")
    chain: RevisionChain[sqlite3.Connection] = RevisionChain((FakeRevision("0001"),))

    with pytest.raises(SchemaVersionAheadError, match="9999"):
        Sqlite().apply_pending(connection, chain, _LOGGER)


def test_apply_pending_does_not_record_a_revision_whose_upgrade_raises(
    connection: sqlite3.Connection,
) -> None:
    backend = Sqlite()

    def _boom(_: sqlite3.Connection) -> None:
        raise ValueError("boom")

    chain: RevisionChain[sqlite3.Connection] = RevisionChain(
        (FakeRevision("0001"), FakeRevision("0002", _boom))
    )

    with pytest.raises(ValueError, match="boom"):
        backend.apply_pending(connection, chain, _LOGGER)

    assert _recorded_revisions(connection) == ["0001"]


def test_apply_pending_rolls_back_a_failing_revisions_own_changes(
    connection: sqlite3.Connection,
) -> None:
    backend = Sqlite()

    def _create_then_fail(connection: sqlite3.Connection) -> None:
        connection.execute("CREATE TABLE should_not_exist (x INTEGER)")
        raise ValueError("boom")

    chain: RevisionChain[sqlite3.Connection] = RevisionChain(
        (FakeRevision("0001", _create_then_fail),)
    )

    with pytest.raises(ValueError, match="boom"):
        backend.apply_pending(connection, chain, _LOGGER)

    tables = [
        row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
    ]
    assert "should_not_exist" not in tables


def test_apply_pending_refuses_a_legacy_transaction_control_connection() -> None:
    connection = sqlite3.connect(":memory:", isolation_level=None)
    chain: RevisionChain[sqlite3.Connection] = RevisionChain((FakeRevision("0001"),))

    with pytest.raises(ValueError, match="autocommit"):
        Sqlite().apply_pending(connection, chain, _LOGGER)


def test_apply_pending_rolls_back_a_failing_revisions_script() -> None:
    def _script_then_fail(connection: sqlite3.Connection) -> None:
        connection.executescript("CREATE TABLE a (x INTEGER); CREATE TABLE b (x INTEGER);")
        raise ValueError("boom")

    chain: RevisionChain[sqlite3.Connection] = RevisionChain(
        (FakeRevision("0001", _script_then_fail),)
    )

    with SqliteInMemory().connect("db") as connection:
        with pytest.raises(ValueError, match="boom"):
            Sqlite().apply_pending(connection, chain, _LOGGER)

        tables = [
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        ]
        assert not {"a", "b"} & set(tables)


def _script(sql: str) -> Callable[[sqlite3.Connection], None]:
    def upgrade(connection: sqlite3.Connection) -> None:
        connection.executescript(sql)

    return upgrade


_PARENT_WITH_CHILD = """
CREATE TABLE parent (id INTEGER PRIMARY KEY);
CREATE TABLE child (parent_id INTEGER REFERENCES parent(id) ON DELETE CASCADE);
INSERT INTO parent VALUES (1);
INSERT INTO child VALUES (1);
"""

# SQLite's procedure for changes ALTER TABLE cannot make.
_REBUILD_PARENT = """
CREATE TABLE new_parent (id INTEGER PRIMARY KEY, name TEXT);
INSERT INTO new_parent (id) SELECT id FROM parent;
DROP TABLE parent;
ALTER TABLE new_parent RENAME TO parent;
"""


def test_apply_pending_rebuilds_a_table_without_cascading_into_rows_referencing_it() -> None:
    chain: RevisionChain[sqlite3.Connection] = RevisionChain(
        (
            FakeRevision("0001", _script(_PARENT_WITH_CHILD)),
            FakeRevision("0002", _script(_REBUILD_PARENT)),
        )
    )

    with SqliteInMemory().connect("db") as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        Sqlite().apply_pending(connection, chain, _LOGGER)

        assert connection.execute("SELECT count(*) FROM child").fetchone()[0] == 1


def test_apply_pending_rejects_a_revision_that_leaves_dangling_references() -> None:
    chain: RevisionChain[sqlite3.Connection] = RevisionChain(
        (
            FakeRevision("0001", _script(_PARENT_WITH_CHILD)),
            FakeRevision("0002", _script("DELETE FROM parent;")),
        )
    )

    with SqliteInMemory().connect("db") as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        with pytest.raises(ForeignKeyViolationError, match="child"):
            Sqlite().apply_pending(connection, chain, _LOGGER)

        assert connection.execute("SELECT count(*) FROM parent").fetchone()[0] == 1


def test_apply_pending_tolerates_violations_that_predate_the_revision() -> None:
    chain: RevisionChain[sqlite3.Connection] = RevisionChain(
        (FakeRevision("0001", _script(_PARENT_WITH_CHILD)),)
    )

    with SqliteInMemory().connect("db") as connection:
        Sqlite().apply_pending(connection, chain, _LOGGER)
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("DELETE FROM parent")
        connection.execute("PRAGMA foreign_keys=ON")
        Sqlite().apply_pending(
            connection,
            RevisionChain((*chain.revisions, FakeRevision("0002", _script("CREATE TABLE t (x);")))),
            _LOGGER,
        )

        assert _recorded_revisions(connection) == ["0002"]


def test_apply_pending_turns_foreign_keys_back_on() -> None:
    chain: RevisionChain[sqlite3.Connection] = RevisionChain((FakeRevision("0001"),))

    with SqliteInMemory().connect("db") as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        Sqlite().apply_pending(connection, chain, _LOGGER)

        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1


@pytest.mark.usefixtures("omd_root")
def test_write_transaction_commits_on_a_connected_database() -> None:
    backend = Sqlite()
    with backend.connect("db", create=True) as connection, write_transaction(connection):
        connection.execute("CREATE TABLE t (x INTEGER)")

    with backend.connect("db") as connection:
        assert connection.execute("SELECT count(*) FROM t").fetchone()[0] == 0


@pytest.mark.usefixtures("omd_root")
def test_connect_with_create_creates_a_missing_database() -> None:
    with Sqlite().connect("db", create=True):
        pass

    assert Sqlite().path("db").exists()


@pytest.mark.usefixtures("omd_root")
def test_connect_refuses_a_missing_database() -> None:
    with pytest.raises(BackendUnavailableError), Sqlite().connect("db"):
        pass

    assert not Sqlite().path("db").exists()


@pytest.mark.usefixtures("omd_root")
def test_connect_preserves_data_written_by_an_earlier_connection() -> None:
    backend = Sqlite()
    with backend.connect("db", create=True) as connection:
        connection.execute("CREATE TABLE t (x INTEGER)")
        connection.execute("INSERT INTO t VALUES (1)")

    with backend.connect("db") as connection:
        assert connection.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 1


@pytest.mark.usefixtures("omd_root")
def test_connect_closes_the_connection_on_exit() -> None:
    with Sqlite().connect("db", create=True) as connection:
        pass

    with pytest.raises(sqlite3.ProgrammingError, match="[Cc]losed database"):
        connection.execute("SELECT 1")


@pytest.mark.usefixtures("omd_root")
def test_connect_leaves_no_write_ahead_log_behind() -> None:
    # A -wal left lying around is what makes replacing the database file
    # dangerous: sqlite replays it onto whatever file the path names next.
    backend = Sqlite()

    with backend.connect("db", create=True) as connection:
        connection.execute("CREATE TABLE t (x INTEGER)")
        connection.execute("INSERT INTO t VALUES (1)")

    assert [path.name for path in backend.path("db").parent.iterdir()] == ["db.sqlite3"]


def test_connect_reopens_the_file_the_path_currently_names(omd_root: Path) -> None:
    backend = Sqlite()
    replacement = omd_root / "restored.sqlite3"
    _make_database(backend.path("db"))
    _make_database(replacement, value=2)
    with backend.connect("db"):
        pass
    replacement.replace(backend.path("db"))

    with backend.connect("db") as connection:
        value = connection.execute("SELECT x FROM t").fetchone()[0]

    assert value == 2


@pytest.mark.usefixtures("unseen_database", "omd_root")
def test_connect_is_quiet_about_a_database_it_creates(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING), Sqlite().connect("db", create=True):
        pass

    assert not caplog.records


@pytest.mark.usefixtures("unseen_database")
def test_connect_reports_a_replaced_database(
    omd_root: Path, caplog: pytest.LogCaptureFixture
) -> None:
    backend = Sqlite()
    replacement = omd_root / "restored.sqlite3"
    _make_database(backend.path("db"))
    _make_database(replacement)
    with backend.connect("db"):
        pass
    replacement.replace(backend.path("db"))

    with caplog.at_level(logging.WARNING), backend.connect("db"):
        pass

    assert "was replaced while in use" in caplog.text


def test_connect_wraps_an_unwritable_location_in_backend_unavailable_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    not_a_directory = tmp_path / "file"
    not_a_directory.touch()
    monkeypatch.setenv("OMD_ROOT", str(not_a_directory))

    with pytest.raises(BackendUnavailableError), Sqlite().connect("db", create=True):
        pass


@pytest.mark.usefixtures("omd_root")
def test_connect_does_not_wrap_errors_raised_inside_the_block() -> None:
    # Without pragmas, opening does not read the damaged page yet.
    backend = Sqlite(configure=lambda _: None)
    _make_database(backend.path("db"))
    with backend.path("db").open("r+b") as damaged:
        damaged.seek(100)
        damaged.write(b"\x00" * 4096)

    with pytest.raises(sqlite3.DatabaseError), backend.connect("db") as connection:
        connection.execute("SELECT * FROM t").fetchall()


@pytest.mark.usefixtures("omd_root")
def test_connect_applies_the_shared_pragmas_by_default() -> None:
    with Sqlite().connect("db", create=True) as connection:
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert connection.execute("PRAGMA synchronous").fetchone()[0] == 1  # NORMAL
        assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


@pytest.mark.usefixtures("omd_root")
def test_connect_applies_the_busy_timeout() -> None:
    with Sqlite(busy_timeout=5).connect("db", create=True) as connection:
        assert connection.execute("PRAGMA busy_timeout").fetchone()[0] == 5000


def test_apply_connection_pragmas_warns_when_wal_is_unavailable(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # A temporary database does not support WAL.
    connection = sqlite3.connect("", isolation_level=None)

    apply_connection_pragmas(connection)

    assert "instead of WAL" in caplog.text


def test_apply_connection_pragmas_is_safe_on_an_in_memory_database() -> None:
    connection = sqlite3.connect(":memory:", isolation_level=None)

    apply_connection_pragmas(connection)
    connection.execute("CREATE TABLE t (id INTEGER)")
    connection.execute("INSERT INTO t VALUES (1)")

    assert connection.execute("SELECT id FROM t").fetchone()[0] == 1


def _recorded_revisions(connection: sqlite3.Connection) -> list[str]:
    return [row[0] for row in connection.execute(f"SELECT id FROM {REVISION_TABLE}")]
