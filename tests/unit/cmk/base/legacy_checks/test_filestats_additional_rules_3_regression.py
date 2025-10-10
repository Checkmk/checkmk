#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="no-untyped-call"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Mapping
from typing import Any

import pytest

from cmk.base.legacy_checks.filestats import (
    check_filestats,
    discover_filestats,
    parse_filestats,
)


@pytest.fixture(name="string_table")
def _string_table() -> list[list[str]]:
    return [
        ["[[[file_stats Filetransfer cofi-premium-world]]]"],
        [
            "{'stat_status': None, 'age': 76216, 'mtime': 1603481501, 'path': u'/opt/filetransfer/data/akb/paag01/cofi#ak/incoming/premium-world-check-day.xml', 'type': 'file', 'size': 9249108}"
        ],
        [
            "{'stat_status': None, 'age': 2025616, 'mtime': 1601532101, 'path': u'/opt/filetransfer/data/akb/paag01/cofi#ak/incoming/premium-world-check-month.xml', 'type': 'file', 'size': 271408990}"
        ],
        [
            "{'stat_status': None, 'age': 517260, 'mtime': 1603040457, 'path': u'/opt/filetransfer/data/akb/paag01/cofi#ak/incoming/premium-world-check-week.xml', 'type': 'file', 'size': 81099075}"
        ],
        ["{'count': 3, 'type': 'summary'}"],
    ]


@pytest.fixture(name="parsed")
def _parsed(string_table: list[list[str]]) -> Mapping[str, Any]:
    return parse_filestats(string_table)


def test_parse_filestats_additional_rules_3_regression(parsed: Mapping[str, Any]) -> None:
    assert "Filetransfer cofi-premium-world" in parsed

    variety, reported_lines = parsed["Filetransfer cofi-premium-world"]
    assert variety == "file_stats"
    assert len(reported_lines) == 4  # 3 files + 1 summary

    # Check summary data
    summary = [item for item in reported_lines if item.get("type") == "summary"][0]
    assert summary["count"] == 3
    assert summary["type"] == "summary"

    # Check file data
    files = [item for item in reported_lines if item.get("type") == "file"]
    assert len(files) == 3

    # Verify specific file details
    day_file = [f for f in files if "day" in f["path"]][0]
    assert day_file["age"] == 76216
    assert day_file["size"] == 9249108
    assert "premium-world-check-day.xml" in day_file["path"]

    month_file = [f for f in files if "month" in f["path"]][0]
    assert month_file["age"] == 2025616
    assert month_file["size"] == 271408990
    assert "premium-world-check-month.xml" in month_file["path"]

    week_file = [f for f in files if "week" in f["path"]][0]
    assert week_file["age"] == 517260
    assert week_file["size"] == 81099075
    assert "premium-world-check-week.xml" in week_file["path"]


def test_discover_filestats_additional_rules_3_regression(parsed: Mapping[str, Any]) -> None:
    result = list(discover_filestats(parsed))
    assert result == [("Filetransfer cofi-premium-world", {})]


def test_check_filestats_additional_rules_3_regression_basic(parsed: Mapping[str, Any]) -> None:
    params = {
        "show_all_files": True,
        "additional_rules": [
            ("DAY", ".*?/premium-world-check-day", {"maxage_oldest": (1, 2)}),
            ("WEEK", ".*?/premium-world-check-week", {"maxage_oldest": (3, 4)}),
            ("MONTH", ".*?/premium-world-check-month", {"maxage_oldest": (5, 6)}),
        ],
    }

    result = list(check_filestats("Filetransfer cofi-premium-world", params, parsed))

    # Should have many results due to additional rules processing
    assert len(result) > 10

    # Check basic file count
    assert result[0][0] == 0  # OK state
    assert "Files in total: 3" in result[0][1]
    assert result[0][2] == [("file_count", 3, None, None)]

    # Check additional rules enabled message
    additional_rules_msg = [r for r in result if len(r) >= 2 and "Additional rules enabled" in r[1]]
    assert len(additional_rules_msg) == 1
    assert additional_rules_msg[0][0] == 0  # OK state


def test_check_filestats_additional_rules_3_regression_day_rule(parsed: Mapping[str, Any]) -> None:
    params = {
        "show_all_files": True,
        "additional_rules": [
            ("DAY", ".*?/premium-world-check-day", {"maxage_oldest": (1, 2)}),
            ("WEEK", ".*?/premium-world-check-week", {"maxage_oldest": (3, 4)}),
            ("MONTH", ".*?/premium-world-check-month", {"maxage_oldest": (5, 6)}),
        ],
    }

    result = list(check_filestats("Filetransfer cofi-premium-world", params, parsed))

    # Find DAY section results
    day_section_start = None
    for i, result_tuple in enumerate(result):
        if len(result_tuple) >= 2 and result_tuple[1] == "\nDAY":
            day_section_start = i
            break

    assert day_section_start is not None

    # Check DAY section messages
    day_results = result[day_section_start : day_section_start + 10]  # Take some results after DAY

    # Find pattern message
    pattern_msg = [
        r for r in day_results if len(r) >= 2 and "Pattern:" in r[1] and "check-day" in r[1]
    ]
    assert len(pattern_msg) == 1
    assert "'.*?/premium-world-check-day'" in pattern_msg[0][1]

    # Find files count for DAY rule
    files_total_msg = [r for r in day_results if len(r) >= 2 and "Files in total: 1" in r[1]]
    assert len(files_total_msg) == 1

    # Find critical age message (age 76216 seconds is way beyond 1-2 second thresholds)
    age_critical_msg = [r for r in day_results if len(r) >= 2 and r[0] == 2 and "Oldest:" in r[1]]
    assert len(age_critical_msg) == 1
    assert "warn/crit at 1 second/2 seconds" in age_critical_msg[0][1]


def test_check_filestats_additional_rules_3_regression_month_rule(
    parsed: Mapping[str, Any],
) -> None:
    params = {
        "show_all_files": True,
        "additional_rules": [
            ("DAY", ".*?/premium-world-check-day", {"maxage_oldest": (1, 2)}),
            ("WEEK", ".*?/premium-world-check-week", {"maxage_oldest": (3, 4)}),
            ("MONTH", ".*?/premium-world-check-month", {"maxage_oldest": (5, 6)}),
        ],
    }

    result = list(check_filestats("Filetransfer cofi-premium-world", params, parsed))

    # Find MONTH section results
    month_section_start = None
    for i, result_tuple in enumerate(result):
        if len(result_tuple) >= 2 and result_tuple[1] == "\nMONTH":
            month_section_start = i
            break

    assert month_section_start is not None

    # Check MONTH section messages
    month_results = result[month_section_start : month_section_start + 10]

    # Find pattern message
    pattern_msg = [
        r for r in month_results if len(r) >= 2 and "Pattern:" in r[1] and "check-month" in r[1]
    ]
    assert len(pattern_msg) == 1
    assert "'.*?/premium-world-check-month'" in pattern_msg[0][1]

    # Find critical age message (age 2025616 seconds is way beyond 5-6 second thresholds)
    age_critical_msg = [r for r in month_results if len(r) >= 2 and r[0] == 2 and "Oldest:" in r[1]]
    assert len(age_critical_msg) == 1
    assert "warn/crit at 5 seconds/6 seconds" in age_critical_msg[0][1]


def test_check_filestats_additional_rules_3_regression_week_rule(parsed: Mapping[str, Any]) -> None:
    params = {
        "show_all_files": True,
        "additional_rules": [
            ("DAY", ".*?/premium-world-check-day", {"maxage_oldest": (1, 2)}),
            ("WEEK", ".*?/premium-world-check-week", {"maxage_oldest": (3, 4)}),
            ("MONTH", ".*?/premium-world-check-month", {"maxage_oldest": (5, 6)}),
        ],
    }

    result = list(check_filestats("Filetransfer cofi-premium-world", params, parsed))

    # Find WEEK section results
    week_section_start = None
    for i, result_tuple in enumerate(result):
        if len(result_tuple) >= 2 and result_tuple[1] == "\nWEEK":
            week_section_start = i
            break

    assert week_section_start is not None

    # Check WEEK section messages
    week_results = result[week_section_start : week_section_start + 10]

    # Find pattern message
    pattern_msg = [
        r for r in week_results if len(r) >= 2 and "Pattern:" in r[1] and "check-week" in r[1]
    ]
    assert len(pattern_msg) == 1
    assert "'.*?/premium-world-check-week'" in pattern_msg[0][1]

    # Find critical age message (age 517260 seconds is way beyond 3-4 second thresholds)
    age_critical_msg = [r for r in week_results if len(r) >= 2 and r[0] == 2 and "Oldest:" in r[1]]
    assert len(age_critical_msg) == 1
    assert "warn/crit at 3 seconds/4 seconds" in age_critical_msg[0][1]


def test_check_filestats_additional_rules_3_regression_remaining_files(
    parsed: Mapping[str, Any],
) -> None:
    params = {
        "show_all_files": True,
        "additional_rules": [
            ("DAY", ".*?/premium-world-check-day", {"maxage_oldest": (1, 2)}),
            ("WEEK", ".*?/premium-world-check-week", {"maxage_oldest": (3, 4)}),
            ("MONTH", ".*?/premium-world-check-month", {"maxage_oldest": (5, 6)}),
        ],
    }

    result = list(check_filestats("Filetransfer cofi-premium-world", params, parsed))

    # Find remaining files message
    remaining_msg = [r for r in result if len(r) >= 2 and "Remaining files: 0" in r[1]]
    assert len(remaining_msg) == 1
    assert remaining_msg[0][0] == 0  # OK state


def test_check_filestats_additional_rules_3_regression_missing_item(
    parsed: Mapping[str, Any],
) -> None:
    result = list(check_filestats("NonExistent", {}, parsed))
    assert result == []
