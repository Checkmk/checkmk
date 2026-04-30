#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Verify Table.upsert / Table.apply_schema delegate correctly."""

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from tests.qa_metrics.db.table import Table
from tests.unit.qa_metrics._db_stubs import FakeDb


@dataclass(frozen=True)
class _DemoRow:
    id_: int
    name: str

    def to_db_dict(self) -> Mapping[str, Any]:
        return asdict(self)


def test_upsert_delegates_to_helpers() -> None:
    table: Table[_DemoRow] = Table(
        name="demo",
        primary_key=("id_",),
        row_type=_DemoRow,
        schema_path=Path("/dev/null"),
    )
    db = FakeDb()

    table.upsert(db, _DemoRow(id_=1, name="x"))  # type: ignore[arg-type]

    assert len(db.cur.queries) == 1
    rendered = db.cur.queries[0]
    assert "INSERT INTO" in rendered
    assert '"demo"' in rendered
    assert 'ON CONFLICT ("id_")' in rendered
    assert db.cur.params[0] == [1, "x"]


def test_apply_schema_reads_file(tmp_path: Path) -> None:
    schema_text = "CREATE TABLE IF NOT EXISTS demo (id_ INT);"
    schema = tmp_path / "schema.sql"
    schema.write_text(schema_text)
    table: Table[_DemoRow] = Table(
        name="demo",
        primary_key=("id_",),
        row_type=_DemoRow,
        schema_path=schema,
    )
    db = FakeDb()

    table.apply_schema(db)  # type: ignore[arg-type]

    assert db.cur.queries == [schema_text]
