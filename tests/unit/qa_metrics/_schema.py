#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Parse column names out of a metric's ``CREATE TABLE`` DDL.

QA-metrics tests assert that a row dataclass' ``to_db_dict()`` keys match the
columns its table declares -- the schema/dataclass alignment that
``tests.qa_metrics.db.Table`` deliberately does not enforce. This is the shared
parser behind those tests; it understands only the plain
``CREATE TABLE [IF NOT EXISTS] <name> (...)`` shape the metrics ship.
"""

import re


def schema_columns(schema_text: str, table: str, *, skip_defaults: bool = False) -> set[str]:
    """Column names declared in the ``CREATE TABLE`` block for ``table``.

    Lines whose first token names a table constraint (``PRIMARY KEY`` etc.) are
    skipped. With ``skip_defaults`` set, columns carrying a ``DEFAULT`` clause
    are skipped too -- those are populated by the DB on first insert and so are
    absent from the row dataclass (e.g. ``first_inserted_at``).
    """
    body_match = re.search(
        rf"CREATE TABLE\s+(?:IF NOT EXISTS\s+)?{re.escape(table)}\s*\((.*?)\);",
        schema_text,
        re.DOTALL | re.IGNORECASE,
    )
    assert body_match is not None, f"CREATE TABLE block for {table} not found"
    skip_keywords = {"PRIMARY", "FOREIGN", "CONSTRAINT", "UNIQUE", "CHECK", "LIKE"}
    columns: set[str] = set()
    for raw in body_match.group(1).splitlines():
        line = raw.strip().rstrip(",")
        if not line or line.startswith("--"):
            continue
        first = line.split()[0]
        if first.upper() in skip_keywords:
            continue
        if skip_defaults and re.search(r"\bDEFAULT\b", line, re.IGNORECASE):
            continue
        columns.add(first)
    return columns
