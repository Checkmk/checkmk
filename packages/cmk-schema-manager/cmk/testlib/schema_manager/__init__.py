#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# mypy 1.19 treats a frozen dataclass as invariant (its synthesized
# __replace__ takes the fields as parameters), so a ManagedDatabase with a
# concrete backend is not a ManagedDatabase[ContextT]. Accept any backend.
# mypy: disable-error-code="explicit-any"
"""Test support for adopters of `cmk.schema_manager`."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Generator
from contextlib import contextmanager, ExitStack, suppress
from dataclasses import replace
from logging import getLogger
from sqlite3 import Connection
from typing import Any, cast, override

from cmk.schema_manager.backend.base import Backend
from cmk.schema_manager.backend.sqlite import REVISION_TABLE, Sqlite, SqliteInMemory
from cmk.schema_manager.managed_database import ManagedDatabase
from cmk.schema_manager.revision import Revision, RevisionChain

_LOGGER = getLogger(__name__)


class FakeRevision[ContextT](Revision[ContextT]):
    def __init__(self, id_: str, upgrade: Callable[[ContextT], None] = lambda _: None) -> None:
        self._id = id_
        self._upgrade = upgrade

    @property
    @override
    def id(self) -> str:
        return self._id

    @override
    def upgrade(self, context: ContextT) -> None:
        self._upgrade(context)


class RevisionTestSuite[ContextT](ABC):
    """Subclass and implement `managed_database`.

    A production database is safe to return: `setup_method` swaps in an
    in-memory backend first.
    """

    _exit_stack: ExitStack
    _context: ContextT
    _ephemeral_database: ManagedDatabase[ContextT, Any]

    @property
    @abstractmethod
    def managed_database(self) -> ManagedDatabase[ContextT, Any]: ...

    @property
    def chain(self) -> RevisionChain[ContextT]:
        return self._ephemeral_database.chain

    def setup_method(self) -> None:
        self._ephemeral_database = replace(
            self.managed_database, backend=_ephemeral_backend(self.managed_database.backend)
        )
        self._exit_stack = ExitStack()
        self._context = self._exit_stack.enter_context(self._ephemeral_database.connect())

    def teardown_method(self) -> None:
        self._exit_stack.close()

    def apply_up_to(self, revision_id: str) -> ContextT:
        """Inclusive."""
        self._ephemeral_database.backend.apply_pending(
            self._context, _chain_up_to(self.chain, revision_id), _LOGGER
        )
        return self._context

    @property
    def connection(self) -> ContextT:
        return self._context

    def test_apply_pending_applies_everything(self) -> None:
        self.apply_up_to(self.chain.revisions[-1].id)

    def test_each_revision_rolls_back_as_a_whole(self) -> None:
        """Fails for a revision that ends the backend's transaction itself."""
        backend = self._ephemeral_database.backend
        for position, revision in enumerate(self.chain):
            applied = self.chain.revisions[:position]
            before = _schema(self._context)
            with suppress(_InjectedFailure):
                backend.apply_pending(
                    self._context, RevisionChain((*applied, _FailAfter(revision))), _LOGGER
                )
            assert _schema(self._context) == before, f"{revision.id} was not rolled back"
            backend.apply_pending(self._context, RevisionChain((*applied, revision)), _LOGGER)


def _ephemeral_backend[ContextT](backend: Backend[ContextT]) -> Backend[ContextT]:
    """An in-memory equivalent of `backend`."""
    if isinstance(backend, Sqlite):
        # mypy cannot narrow ContextT from isinstance; Sqlite implies ContextT = Connection.
        return cast(Backend[ContextT], SqliteInMemory(configure=backend.configure))
    raise NotImplementedError(f"no ephemeral backend conversion for {type(backend).__name__}")


class _InjectedFailure(Exception):
    pass


class _FailAfter[ContextT](Revision[ContextT]):
    def __init__(self, revision: Revision[ContextT]) -> None:
        self._revision = revision

    @property
    @override
    def id(self) -> str:
        return self._revision.id

    @override
    def upgrade(self, context: ContextT) -> None:
        self._revision.upgrade(context)
        raise _InjectedFailure


def _schema(context: object) -> list[tuple[object, ...]]:
    if not isinstance(context, Connection):
        raise NotImplementedError(f"no schema snapshot for {type(context).__name__}")
    return [
        tuple(row)
        for row in context.execute(
            "SELECT type, name, sql FROM sqlite_master WHERE tbl_name != ? ORDER BY 1, 2",
            (REVISION_TABLE,),
        )
    ]


def _chain_up_to[ContextT](
    chain: RevisionChain[ContextT], revision_id: str
) -> RevisionChain[ContextT]:
    ids = [revision.id for revision in chain]
    if revision_id not in ids:
        raise ValueError(f"No revision {revision_id!r} in chain")
    return RevisionChain(chain.revisions[: ids.index(revision_id) + 1])


@contextmanager
def migrated_connection[ContextT](  # type: ignore[misc]  # Any: see the module header
    database: ManagedDatabase[ContextT, Any],
) -> Generator[ContextT]:
    """A connection to an empty database at the latest schema, for tests of
    code that reads or writes it. Closed again on leaving the block.

    A production database is safe to pass: an in-memory backend is swapped
    in first, so each test starts from an empty database:

        with migrated_connection(schema_manager_example) as connection:
            assert read_items(connection) == []
    """
    ephemeral_database = replace(database, backend=_ephemeral_backend(database.backend))
    with ephemeral_database.connect(create=True) as context:
        ephemeral_database.backend.apply_pending(context, ephemeral_database.chain, _LOGGER)
        yield context
