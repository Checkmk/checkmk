#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import sqlite3

import pytest

from cmk.schema_manager._mechanism import ensure_schema
from cmk.schema_manager.backend.sqlite import Sqlite
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
