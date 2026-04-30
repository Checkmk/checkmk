#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Smoke-test the SQL rendered by helpers without hitting a real postgres."""

from tests.qa_metrics.db.helpers import upsert_record
from tests.unit.qa_metrics._db_stubs import FakeDb


def test_upsert_record_renders_on_conflict() -> None:
    db = FakeDb()

    upsert_record(
        db,  # type: ignore[arg-type]
        table="cmk_change_tested",
        conflict_columns=["werk_id", "branch"],
        insert_values={"werk_id": 1, "branch": "master", "has_test": True},
    )

    assert len(db.cur.queries) == 1
    rendered = db.cur.queries[0]
    assert "INSERT INTO" in rendered
    assert 'ON CONFLICT ("werk_id", "branch")' in rendered
    assert "DO UPDATE SET" in rendered
    assert '"has_test" = EXCLUDED."has_test"' in rendered
    assert db.cur.params[0] == [1, "master", True]
