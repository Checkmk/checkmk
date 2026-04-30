#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import re
from datetime import datetime, UTC

from tests.qa_metrics.change_quality.rows import CHANGE_TESTED, ChangeTestedRow


def _row() -> ChangeTestedRow:
    return ChangeTestedRow(
        werk_id=15155,
        branch="2.4.0",
        werk_class="fix",
        werk_component="checks",
        werk_date=datetime(2023, 3, 8, 12, 0, tzinfo=UTC),
        edition="community",
        level=1,
        title="sap_hana_status: Handle WARNING status correctly",
        git_commit_hash="abc1234567890",
        commit_time=datetime(2023, 3, 8, 12, 5, tzinfo=UTC),
        author_email="dev@example.com",
        subject="sap_hana_status: Handle WARNING status correctly",
        gerrit_change_id="I0123456789abcdef",
        source_component="plugins/sap_hana",
        has_test=True,
        files_changed=3,
    )


def _row_required_columns(schema_text: str) -> set[str]:
    """Columns from ``CREATE TABLE`` that the row dataclass must supply.

    Excludes columns with a ``DEFAULT`` clause -- those are populated by the
    DB on first insert (see schema.sql's note about ``first_inserted_at``).
    """
    body_match = re.search(r"CREATE TABLE[^(]*\((.*?)\);", schema_text, re.DOTALL | re.IGNORECASE)
    assert body_match is not None, "CREATE TABLE block not found in schema"
    skip_keywords = {"PRIMARY", "FOREIGN", "CONSTRAINT", "UNIQUE", "CHECK", "LIKE"}
    columns: set[str] = set()
    for raw in body_match.group(1).splitlines():
        line = raw.strip().rstrip(",")
        if not line or line.startswith("--"):
            continue
        first = line.split()[0]
        if first.upper() in skip_keywords:
            continue
        if re.search(r"\bDEFAULT\b", line, re.IGNORECASE):
            continue
        columns.add(first)
    return columns


def test_to_db_dict_keys_match_schema_columns() -> None:
    """Catches dataclass/schema drift -- the gap called out in db/table.py."""
    schema_text = CHANGE_TESTED.schema_path.read_text(encoding="utf-8")
    expected = _row_required_columns(schema_text)
    assert expected, "schema parser found no columns -- parser is broken"
    assert set(_row().to_db_dict()) == expected


def test_to_db_dict_preserves_values() -> None:
    row = _row()
    db_dict = row.to_db_dict()
    assert db_dict["werk_id"] == 15155
    assert db_dict["branch"] == "2.4.0"
    assert db_dict["werk_class"] == "fix"
    assert db_dict["has_test"] is True
    assert db_dict["files_changed"] == 3
    assert db_dict["gerrit_change_id"] == "I0123456789abcdef"
