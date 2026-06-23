#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from datetime import datetime, UTC

from tests.qa_metrics.unit_test_coverage.rows import (
    ModuleCoverageRow,
    PER_MODULE,
    TOTAL,
    TotalCoverageRow,
)
from tests.unit.qa_metrics._schema import schema_columns


def test_total_to_db_dict_keys_match_schema_columns() -> None:
    schema_text = TOTAL.schema_path.read_text(encoding="utf-8")
    expected = schema_columns(schema_text, TOTAL.name)
    assert expected, "schema parser found no columns -- parser is broken"
    assert set(_total_row().to_db_dict()) == expected


def test_module_to_db_dict_keys_match_schema_columns() -> None:
    schema_text = PER_MODULE.schema_path.read_text(encoding="utf-8")
    expected = schema_columns(schema_text, PER_MODULE.name)
    assert expected, "schema parser found no columns -- parser is broken"
    assert set(_module_row().to_db_dict()) == expected


def test_primary_keys_are_schema_columns() -> None:
    """The Table primary keys must be real columns of their tables."""
    schema_text = TOTAL.schema_path.read_text(encoding="utf-8")
    assert set(TOTAL.primary_key) <= schema_columns(schema_text, TOTAL.name)
    assert set(PER_MODULE.primary_key) <= schema_columns(schema_text, PER_MODULE.name)


def test_total_to_db_dict_preserves_values() -> None:
    assert _total_row().to_db_dict() == {
        "commit_hash": "abc1234",
        "covered_lines": 100,
        "total_lines": 200,
        "covered_functions": 30,
        "total_functions": 60,
        "commit_time": datetime(2025, 10, 16, 12, 5, 43, tzinfo=UTC),
    }


def test_module_to_db_dict_preserves_values() -> None:
    assert _module_row().to_db_dict() == {
        "module_path": "cmk/base/foo.py",
        "covered_lines": 10,
        "total_lines": 20,
        "covered_functions": 3,
        "total_functions": 6,
        "commit_hash": "abc1234",
        "commit_time": datetime(2025, 10, 16, 12, 5, 43, tzinfo=UTC),
    }


def _total_row() -> TotalCoverageRow:
    return TotalCoverageRow(
        commit_hash="abc1234",
        covered_lines=100,
        total_lines=200,
        covered_functions=30,
        total_functions=60,
        commit_time=datetime(2025, 10, 16, 12, 5, 43, tzinfo=UTC),
    )


def _module_row() -> ModuleCoverageRow:
    return ModuleCoverageRow(
        module_path="cmk/base/foo.py",
        covered_lines=10,
        total_lines=20,
        covered_functions=3,
        total_functions=6,
        commit_hash="abc1234",
        commit_time=datetime(2025, 10, 16, 12, 5, 43, tzinfo=UTC),
    )
