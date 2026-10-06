#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import sqlite3
from collections.abc import Sequence
from typing import Literal

import pytest

from cmk.schema_manager._mechanism import ensure_schema, ensure_schemas_on_update
from cmk.schema_manager.backend.sqlite import ensure_sqlite_up_to_date, REVISION_TABLE, Sqlite
from cmk.schema_manager.managed_database import ManagedDatabase
from cmk.schema_manager.revision import RevisionChain
from cmk.testlib.schema_manager import FakeRevision

_LOGGER = logging.getLogger("test")


@pytest.mark.usefixtures("omd_root")
def test_ensure_schema_applies_pending_revisions() -> None:
    applied: list[str] = []
    backend = Sqlite()
    chain: RevisionChain[sqlite3.Connection] = RevisionChain(
        (FakeRevision("0001", lambda _: applied.append("0001")),)
    )

    ensure_schema(
        ManagedDatabase(name="db", backend=backend, chain=chain, omd_lifecycle=[]), _LOGGER
    )

    assert applied == ["0001"]


@pytest.mark.usefixtures("omd_root")
def test_ensure_schema_closes_the_connection_afterwards() -> None:
    captured: list[sqlite3.Connection] = []
    backend = Sqlite(configure=captured.append)
    chain: RevisionChain[sqlite3.Connection] = RevisionChain((FakeRevision("0001"),))

    ensure_schema(
        ManagedDatabase(name="db", backend=backend, chain=chain, omd_lifecycle=[]), _LOGGER
    )

    with pytest.raises(sqlite3.ProgrammingError):
        captured[0].execute("SELECT 1")


def _create_table(connection: sqlite3.Connection) -> None:
    connection.execute("CREATE TABLE t (id INTEGER)")


def _fail(_connection: sqlite3.Connection) -> None:
    raise ValueError


def _database(
    name: str,
    lifecycle: Sequence[Literal["create", "update"]],
    revision: FakeRevision[sqlite3.Connection] = FakeRevision("0001", _create_table),
) -> ManagedDatabase[sqlite3.Connection]:
    return ManagedDatabase(
        name=name, backend=Sqlite(), chain=RevisionChain((revision,)), omd_lifecycle=lifecycle
    )


def _applied_revisions(name: str) -> list[str]:
    with sqlite3.connect(Sqlite().path(name)) as connection:
        return [row[0] for row in connection.execute(f"SELECT id FROM {REVISION_TABLE}")]


def _existing_database(name: str) -> None:
    path = Sqlite().path(name)
    path.parent.mkdir(parents=True)
    path.touch()


@pytest.mark.usefixtures("omd_root")
def test_ensure_schemas_on_update_applies_pending_revisions_to_an_existing_database() -> None:
    _existing_database("feature_a")

    ensure_schemas_on_update([_database("feature_a", ["update"])], _LOGGER)

    assert _applied_revisions("feature_a") == ["0001"]


@pytest.mark.usefixtures("omd_root")
def test_ensure_schemas_on_update_skips_a_missing_update_only_database() -> None:
    ensure_schemas_on_update([_database("feature_b", ["update"])], _LOGGER)

    assert not Sqlite().path("feature_b").exists()


@pytest.mark.usefixtures("omd_root")
def test_ensure_schemas_on_update_creates_a_missing_database_opted_into_create() -> None:
    ensure_schemas_on_update([_database("feature_c", ["create", "update"])], _LOGGER)

    assert _applied_revisions("feature_c") == ["0001"]


@pytest.mark.usefixtures("omd_root")
def test_ensure_schemas_on_update_tries_every_database_before_failing() -> None:
    databases = [
        _database("feature_d", ["create", "update"], FakeRevision("0001", _fail)),
        _database("feature_e", ["create", "update"]),
    ]

    with pytest.raises(RuntimeError, match="feature_d"):
        ensure_schemas_on_update(databases, _LOGGER)

    assert _applied_revisions("feature_e") == ["0001"]


@pytest.mark.usefixtures("omd_root", "registered_fixture_databases")
def test_ensure_sqlite_up_to_date_handles_the_discovered_update_databases() -> None:
    ensure_sqlite_up_to_date(_LOGGER)

    assert _applied_revisions("create_and_update") == ["0001"]
    assert not Sqlite().exists("update_only")
