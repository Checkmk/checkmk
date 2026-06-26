#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from tests.qa_metrics.unit_test_coverage.summary import (
    calculate_total_coverage,
    CoverageStats,
    parse_lcov,
    RawStats,
)


def test_parse_lcov_counts_lcov_2_x_function_records() -> None:
    """lcov 2.x emits FNL/FNA; function hits must be read from FNA records."""
    assert parse_lcov(
        [
            "SF:cmk/foo.py",
            "FNL:0,10",
            "FNA:0,3,covered_func",
            "FNL:1,20",
            "FNA:1,0,uncovered_func",
            "DA:10,3",
            "DA:11,0",
            "end_of_record",
        ]
    ) == {"cmk/foo.py": RawStats(lines=2, lines_covered=1, functions=2, functions_covered=1)}


def test_parse_lcov_handles_function_names_containing_commas() -> None:
    assert parse_lcov(["SF:cmk/foo.py", "FNA:0,1,outer.<locals>.inner,weird", "end_of_record"]) == {
        "cmk/foo.py": RawStats(lines=0, lines_covered=0, functions=1, functions_covered=1)
    }


def test_parse_lcov_ignores_records_before_first_source_file() -> None:
    assert parse_lcov(["TN:", "SF:cmk/baz.py", "DA:1,1", "end_of_record"]) == {
        "cmk/baz.py": RawStats(lines=1, lines_covered=1, functions=0, functions_covered=0)
    }


def test_calculate_total_coverage_sums_across_files() -> None:
    file_data = parse_lcov(
        [
            "SF:cmk/a.py",
            "FNA:0,1,a",
            "FNA:1,0,b",
            "DA:1,1",
            "end_of_record",
            "SF:cmk/b.py",
            "FNA:0,1,c",
            "DA:1,0",
            "DA:2,1",
            "end_of_record",
        ]
    )

    assert calculate_total_coverage(file_data) == CoverageStats(
        lines_coverage_percent=66.67,
        functions_coverage_percent=66.67,
        covered_lines=2,
        total_lines=3,
        covered_functions=2,
        total_functions=3,
    )
