#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import sqlite3
from collections.abc import Callable, Generator
from contextlib import contextmanager
from logging import Logger
from typing import override

import pytest

from cmk.schema_manager.backend.base import Backend
from cmk.schema_manager.backend.sqlite import Sqlite, SqliteInMemory
from cmk.schema_manager.managed_database import ManagedDatabase
from cmk.schema_manager.revision import RevisionChain
from cmk.testlib.schema_manager import FakeRevision, migrated_connection, RevisionTestSuite


def _chain(*upgrades: Callable[[sqlite3.Connection], None]) -> RevisionChain[sqlite3.Connection]:
    return RevisionChain(
        tuple(FakeRevision(f"{i:04d}", upgrade) for i, upgrade in enumerate(upgrades, start=1))
    )


class _Suite(RevisionTestSuite[sqlite3.Connection]):
    """Uses the real backend; setup_method must never touch it."""

    def __init__(self, chain: RevisionChain[sqlite3.Connection]) -> None:
        self._chain = chain

    @property
    @override
    def managed_database(self) -> ManagedDatabase[sqlite3.Connection]:
        return ManagedDatabase(
            name="sample",
            backend=Sqlite(),
            chain=self._chain,
            omd_lifecycle=["update"],
        )


class _FakeBackend(Backend[object]):
    """A minimal non-`Sqlite` backend, to exercise `_ephemeral_backend`'s fallback."""

    @override
    @contextmanager
    def connect(self, name: str, *, create: bool = False) -> Generator[object]:
        yield object()

    @override
    def exists(self, name: str) -> bool:
        return True

    @override
    def apply_pending(self, context: object, chain: RevisionChain[object], logger: Logger) -> None:
        pass


class _SuiteWithUnsupportedBackend(RevisionTestSuite[object]):
    @property
    @override
    def managed_database(self) -> ManagedDatabase[object]:
        return ManagedDatabase(
            name="sample",
            backend=_FakeBackend(),
            chain=RevisionChain((FakeRevision("0001"),)),
            omd_lifecycle=[],
        )


def test_apply_up_to_applies_only_revisions_up_to_the_given_id() -> None:
    applied: list[str] = []
    suite = _Suite(_chain(lambda _: applied.append("0001"), lambda _: applied.append("0002")))
    suite.setup_method()
    try:
        suite.apply_up_to("0001")
    finally:
        suite.teardown_method()

    assert applied == ["0001"]


def test_apply_up_to_returns_a_usable_context() -> None:
    def _create_table(connection: sqlite3.Connection) -> None:
        connection.execute("CREATE TABLE t (id INTEGER)")

    suite = _Suite(_chain(_create_table))
    suite.setup_method()
    try:
        connection = suite.apply_up_to("0001")
        connection.execute("INSERT INTO t (id) VALUES (1)")
    finally:
        suite.teardown_method()


@pytest.mark.usefixtures("omd_root")
def test_setup_method_never_touches_the_real_backend() -> None:
    suite = _Suite(_chain(lambda _: None))
    suite.setup_method()
    try:
        suite.apply_up_to("0001")
    finally:
        suite.teardown_method()

    assert not Sqlite().path("sample").exists()


def test_setup_method_rejects_a_backend_with_no_ephemeral_equivalent() -> None:
    suite = _SuiteWithUnsupportedBackend()
    with pytest.raises(NotImplementedError, match="_FakeBackend"):
        suite.setup_method()


def test_connection_is_the_same_context_apply_up_to_uses() -> None:
    suite = _Suite(_chain(lambda _: None))
    suite.setup_method()
    try:
        context = suite.apply_up_to("0001")
        assert suite.connection is context
    finally:
        suite.teardown_method()


def test_apply_up_to_rejects_an_unknown_revision_id() -> None:
    suite = _Suite(_chain(lambda _: None))
    suite.setup_method()
    try:
        with pytest.raises(ValueError, match="No revision 'does-not-exist' in chain"):
            suite.apply_up_to("does-not-exist")
    finally:
        suite.teardown_method()


def test_test_apply_pending_applies_everything_passes_for_a_healthy_chain() -> None:
    suite = _Suite(_chain(lambda _: None, lambda _: None))
    suite.setup_method()
    try:
        suite.test_apply_pending_applies_everything()
    finally:
        suite.teardown_method()


def test_test_apply_pending_applies_everything_fails_for_a_broken_revision() -> None:
    def _boom(_: sqlite3.Connection) -> None:
        raise ValueError("boom")

    suite = _Suite(_chain(_boom))
    suite.setup_method()
    try:
        with pytest.raises(ValueError, match="boom"):
            suite.test_apply_pending_applies_everything()
    finally:
        suite.teardown_method()


def test_test_each_revision_rolls_back_as_a_whole_passes_for_a_script() -> None:
    def _script(connection: sqlite3.Connection) -> None:
        connection.executescript("CREATE TABLE a (x INTEGER); CREATE TABLE b (x INTEGER);")

    suite = _Suite(_chain(_script))
    suite.setup_method()
    try:
        suite.test_each_revision_rolls_back_as_a_whole()
    finally:
        suite.teardown_method()


def test_test_each_revision_rolls_back_as_a_whole_fails_for_a_revision_that_commits() -> None:
    def _create_then_commit(connection: sqlite3.Connection) -> None:
        connection.execute("CREATE TABLE t (id INTEGER)")
        connection.execute("COMMIT")

    suite = _Suite(_chain(_create_then_commit))
    suite.setup_method()
    try:
        with pytest.raises(AssertionError, match="0001 was not rolled back"):
            suite.test_each_revision_rolls_back_as_a_whole()
    finally:
        suite.teardown_method()


def test_migrated_connection_has_every_revision_applied() -> None:
    def _create_table(connection: sqlite3.Connection) -> None:
        connection.execute("CREATE TABLE t (id INTEGER)")

    database = ManagedDatabase(
        name="sample",
        backend=SqliteInMemory(),
        chain=_chain(_create_table),
        omd_lifecycle=["update"],
    )

    with migrated_connection(database) as connection:
        connection.execute("INSERT INTO t (id) VALUES (1)")
        assert [row["id"] for row in connection.execute("SELECT id FROM t")] == [1]


def test_migrated_connection_closes_the_connection_afterwards() -> None:
    database = ManagedDatabase(
        name="sample",
        backend=SqliteInMemory(),
        chain=_chain(lambda _: None),
        omd_lifecycle=["update"],
    )

    with migrated_connection(database) as connection:
        pass

    with pytest.raises(sqlite3.ProgrammingError):
        connection.execute("SELECT 1")


@pytest.mark.usefixtures("omd_root")
def test_migrated_connection_never_touches_the_real_backend() -> None:
    database = ManagedDatabase(
        name="sample",
        backend=Sqlite(),
        chain=_chain(lambda _: None),
        omd_lifecycle=["update"],
    )

    with migrated_connection(database):
        pass

    assert not Sqlite().path("sample").exists()
