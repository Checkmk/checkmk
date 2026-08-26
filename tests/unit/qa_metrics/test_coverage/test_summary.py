#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from tests.qa_metrics.test_coverage.summary import (
    calculate_total_coverage,
    CoverageStats,
    parse_lcov,
    RawStats,
)


def test_parse_lcov_counts_a_hit_line_as_covered() -> None:
    assert parse_lcov(["SF:cmk/foo.py", "DA:10,3", "end_of_record"]) == {
        "cmk/foo.py": RawStats(lines=1, lines_covered=1, functions=0, functions_covered=0)
    }


def test_parse_lcov_counts_a_zero_hit_line_as_uncovered() -> None:
    assert parse_lcov(["SF:cmk/foo.py", "DA:10,0", "end_of_record"]) == {
        "cmk/foo.py": RawStats(lines=1, lines_covered=0, functions=0, functions_covered=0)
    }


def test_parse_lcov_counts_lines_and_functions_independently() -> None:
    assert parse_lcov(
        [
            "SF:cmk/foo.py",
            "DA:10,1",
            "DA:11,0",
            "FNDA:5,covered",
            "FNDA:0,uncovered",
            "end_of_record",
        ]
    ) == {"cmk/foo.py": RawStats(lines=2, lines_covered=1, functions=2, functions_covered=1)}


def test_parse_lcov_counts_a_line_once_however_often_it_appears() -> None:
    """These counts are what the dashboard publishes; a repeated file must not double them."""
    assert parse_lcov(
        [
            "SF:cmk/foo.py",
            "DA:10,1",
            "end_of_record",
            "SF:cmk/foo.py",
            "DA:10,1",
            "DA:11,0",
            "end_of_record",
        ]
    ) == {"cmk/foo.py": RawStats(lines=2, lines_covered=1, functions=0, functions_covered=0)}


def test_parse_lcov_takes_the_highest_hit_count_for_a_repeated_line() -> None:
    """A line one record misses and another hits is covered, not uncovered."""
    assert parse_lcov(
        ["SF:cmk/foo.py", "DA:10,0", "end_of_record", "SF:cmk/foo.py", "DA:10,4", "end_of_record"]
    ) == {"cmk/foo.py": RawStats(lines=1, lines_covered=1, functions=0, functions_covered=0)}


def test_parse_lcov_keeps_two_functions_sharing_a_name() -> None:
    """A closure defined in both branches of an if/else: one name, two functions."""
    assert parse_lcov(
        [
            "SF:cmk/foo.py",
            "FNDA:1,outer.<locals>.inner",
            "FNDA:0,outer.<locals>.inner",
            "end_of_record",
        ]
    ) == {"cmk/foo.py": RawStats(lines=0, lines_covered=0, functions=2, functions_covered=1)}


def test_parse_lcov_counts_function_records() -> None:
    """Both producers emit FN/FNDA; hits are FNDA's first field."""
    assert parse_lcov(
        [
            "SF:cmk/foo.py",
            "FN:10,covered_func",
            "FNDA:3,covered_func",
            "FN:20,uncovered_func",
            "FNDA:0,uncovered_func",
            "DA:10,3",
            "DA:11,0",
            "end_of_record",
        ]
    ) == {"cmk/foo.py": RawStats(lines=2, lines_covered=1, functions=2, functions_covered=1)}


def test_parse_lcov_handles_function_names_containing_commas() -> None:
    assert parse_lcov(["SF:cmk/foo.py", "FNDA:1,outer.<locals>.inner,weird", "end_of_record"]) == {
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
            "FNDA:1,a",
            "FNDA:0,b",
            "DA:1,1",
            "end_of_record",
            "SF:cmk/b.py",
            "FNDA:1,c",
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
