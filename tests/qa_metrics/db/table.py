#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Light binding from a row dataclass to a postgres table.

A ``Table[RowT]`` wraps a metric's table identity (name, primary key, row type,
schema-file path) and exposes ``upsert`` / ``apply_schema`` so callers stop
repeating ``conflict_columns=...`` and ``Path(__file__).with_name(...)``.

Not an ORM: schema is still declared in plain SQL, fields are still declared on
the dataclass. The binding only removes repetition; it does not enforce
schema/dataclass alignment.
"""

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .connection import MetabasePostgres
from .helpers import upsert_record

logger = logging.getLogger(__name__)


def apply_schema_file(db: MetabasePostgres, sql_path: Path) -> None:
    """Execute the SQL in ``sql_path`` against ``db``.

    Each metric ships its DDL as a plain ``.sql`` file using
    ``CREATE TABLE IF NOT EXISTS`` / ``CREATE INDEX IF NOT EXISTS``; this
    helper just runs it. Not a migration framework.
    """
    sql_text = sql_path.read_text(encoding="utf-8")
    with db.cursor() as cursor:
        cursor.execute(sql_text)
    logger.info("Applied schema from %s", sql_path)


class DbRow(Protocol):
    """Anything with a ``to_db_dict()`` method that yields column → value."""

    def to_db_dict(self) -> Mapping[str, Any]: ...


@dataclass(frozen=True)
class Table[RowT: DbRow]:
    """Identity of a postgres table consumed by a metric."""

    name: str
    primary_key: tuple[str, ...]
    row_type: type[RowT]
    schema_path: Path

    def upsert(self, db: MetabasePostgres, row: RowT) -> None:
        upsert_record(
            db,
            self.name,
            list(self.primary_key),
            row.to_db_dict(),
        )

    def apply_schema(self, db: MetabasePostgres) -> None:
        apply_schema_file(db, self.schema_path)
