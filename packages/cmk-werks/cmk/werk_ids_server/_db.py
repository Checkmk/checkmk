#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import sqlite3
from collections.abc import Sequence
from pathlib import Path

_logger = logging.getLogger(__name__)


def init_db(db: Path, start: int) -> None:
    db.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db) as conn:
        table_exists = (
            conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='ids'").fetchone()
            is not None
        )
        if not table_exists:
            conn.execute("CREATE TABLE ids (value INTEGER NOT NULL)")
            conn.execute(
                "INSERT INTO ids (value) SELECT ? WHERE NOT EXISTS (SELECT 1 FROM ids)",
                (start,),
            )
    if table_exists:
        _logger.info("Database %r already exists", db)
    else:
        _logger.info("Init database: %r, start ID: %r", db, start)


def reserve(db: Path, to_be_reserved: int) -> Sequence[int]:
    with sqlite3.connect(db) as conn:
        row = conn.execute(
            "UPDATE ids SET value = value + ?1 RETURNING value - ?1 + 1, value",
            (to_be_reserved,),
        ).fetchone()

    if row is None:
        raise RuntimeError("Failed to reserve IDs")

    return list(range(int(row[0]), int(row[1]) + 1))
