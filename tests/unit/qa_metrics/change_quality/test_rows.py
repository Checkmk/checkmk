#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from datetime import datetime, UTC

from tests.qa_metrics.change_quality.rows import CHANGE_TESTED, ChangeTestedRow
from tests.unit.qa_metrics._schema import schema_columns


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


def test_to_db_dict_keys_match_schema_columns() -> None:
    """Catches dataclass/schema drift -- the gap called out in db/table.py."""
    schema_text = CHANGE_TESTED.schema_path.read_text(encoding="utf-8")
    expected = schema_columns(schema_text, CHANGE_TESTED.name, skip_defaults=True)
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
