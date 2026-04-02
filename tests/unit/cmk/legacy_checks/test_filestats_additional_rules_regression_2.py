#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from typing import Any

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.legacy_checks.filestats import (
    check_filestats,
    discover_filestats,
    parse_filestats,
)


@pytest.fixture(name="string_table")
def _string_table() -> list[list[str]]:
    return [
        ["[[[file_stats foo]]]"],
        [
            "{'age': 21374, 'mtime': 1600757875, 'path': '/var/log/boot.log', 'size': 141894, 'stat_status': 'ok', 'type': 'file'}"
        ],
        [
            "{'stat_status': 'ok', 'age': 0, 'mtime': 160779533, 'path': '/var/log/syslog', 'type': 'file', 'size': 13874994}"
        ],
        [
            "{'stat_status': 'ok', 'age': 4079566, 'mtime': 1596699967, 'path': '/var/log/syslog.3.gz', 'type': 'file', 'size': 5313033}"
        ],
        [
            "{'stat_status': 'ok', 'age': 1661230, 'mtime': 1599118303, 'path': '/var/log/syslog.1', 'type': 'file', 'size': 22121937}"
        ],
        [
            "{'stat_status': 'ok', 'age': 4583773, 'mtime': 1596195760, 'path': '/var/log/apport.log.2.gz', 'type': 'file', 'size': 479}"
        ],
        ["{'type': 'summary', 'count': 5}"],
    ]


@pytest.fixture(name="parsed")
def _parsed(
    string_table: list[list[str]],
) -> dict[str, tuple[str, list[dict[str, Any]]]]:
    return parse_filestats(string_table)


def test_parse_filestats_additional_rules_regression_2(
    parsed: dict[str, tuple[str, list[dict[str, Any]]]],
) -> None:
    assert "foo" in parsed

    variety, reported_lines = parsed["foo"]
    assert variety == "file_stats"
    assert len(reported_lines) == 6  # 5 files + 1 summary

    # Check summary data
    summary = [item for item in reported_lines if item.get("type") == "summary"][0]
    assert summary["count"] == 5
    assert summary["type"] == "summary"

    # Check file data
    files = [item for item in reported_lines if item.get("type") == "file"]
    assert len(files) == 5

    # Verify specific file details
    boot_log = [f for f in files if "boot.log" in f["path"]][0]
    assert boot_log["age"] == 21374
    assert boot_log["size"] == 141894
    assert boot_log["stat_status"] == "ok"

    syslog = [f for f in files if f["path"] == "/var/log/syslog"][0]
    assert syslog["age"] == 0
    assert syslog["size"] == 13874994
    assert syslog["stat_status"] == "ok"

    apport_log = [f for f in files if "apport" in f["path"]][0]
    assert apport_log["age"] == 4583773
    assert apport_log["size"] == 479
    assert apport_log["stat_status"] == "ok"


def test_discover_filestats_additional_rules_regression_2(
    parsed: dict[str, tuple[str, list[dict[str, Any]]]],
) -> None:
    result = list(discover_filestats(parsed))
    assert result == [Service(item="foo")]


def _get_text(r: Result | Metric) -> str:
    """Helper to get displayable text from a Result or Metric."""
    if isinstance(r, Result):
        return r.summary or r.details or ""
    return ""


def test_check_filestats_additional_rules_regression_2_basic(
    parsed: dict[str, tuple[str, list[dict[str, Any]]]],
) -> None:
    params = {
        "maxsize_largest": (4, 5),
        "additional_rules": [
            ("Sys-related files", "/var/log/sys*", {"maxsize_largest": (1, 2)}),
            ("", "/var/log/app*", {"maxsize_largest": (100, 200)}),
        ],
        "show_all_files": True,
    }

    result = list(check_filestats("foo", params, parsed))

    # Should have many results due to additional rules processing
    assert len(result) > 15

    # Check basic file count - first result should be file count
    first_result = result[0]
    assert isinstance(first_result, Result)
    assert first_result.state == State.OK
    assert "Files in total: 5" in first_result.summary

    # Second result is a Metric
    assert isinstance(result[1], Metric)
    assert result[1].name == "file_count"
    assert result[1].value == 5.0

    # Check additional rules enabled message
    additional_rules_msg = [
        r for r in result if isinstance(r, Result) and "Additional rules enabled" in _get_text(r)
    ]
    assert len(additional_rules_msg) == 1
    assert additional_rules_msg[0].state == State.OK


def test_check_filestats_additional_rules_regression_2_size_thresholds(
    parsed: dict[str, tuple[str, list[dict[str, Any]]]],
) -> None:
    params = {
        "maxsize_largest": (4, 5),  # Very small thresholds to trigger alerts
        "additional_rules": [
            ("Sys-related files", "/var/log/sys*", {"maxsize_largest": (1, 2)}),
            ("", "/var/log/app*", {"maxsize_largest": (100, 200)}),
        ],
        "show_all_files": True,
    }

    result = list(check_filestats("foo", params, parsed))

    # Should have critical alerts due to small size thresholds
    critical_results = [r for r in result if isinstance(r, Result) and r.state == State.CRIT]
    assert len(critical_results) >= 3  # At least 3 critical size violations

    # Check that threshold messages are present
    threshold_messages = [
        r for r in result if isinstance(r, Result) and "warn/crit at" in _get_text(r)
    ]
    assert len(threshold_messages) >= 3


def test_check_filestats_additional_rules_regression_2_sys_related_files(
    parsed: dict[str, tuple[str, list[dict[str, Any]]]],
) -> None:
    params = {
        "maxsize_largest": (4, 5),
        "additional_rules": [
            ("Sys-related files", "/var/log/sys*", {"maxsize_largest": (1, 2)}),
            ("", "/var/log/app*", {"maxsize_largest": (100, 200)}),
        ],
        "show_all_files": True,
    }

    result = list(check_filestats("foo", params, parsed))

    # Find Sys-related files section (now a notice, not summary)
    sys_section_start = None
    for i, result_obj in enumerate(result):
        if isinstance(result_obj, Result) and result_obj.details == "Sys-related files":
            sys_section_start = i
            break

    assert sys_section_start is not None

    # Check Sys-related files section messages
    sys_results = result[sys_section_start : sys_section_start + 10]

    # Find pattern message
    pattern_msg = [
        r
        for r in sys_results
        if isinstance(r, Result) and "Pattern:" in _get_text(r) and "sys*" in _get_text(r)
    ]
    assert len(pattern_msg) == 1
    assert "'/var/log/sys*'" in pattern_msg[0].summary

    # Should find 3 sys-related files (syslog, syslog.1, syslog.3.gz)
    files_total_msg = [
        r for r in sys_results if isinstance(r, Result) and "Files in total: 3" in _get_text(r)
    ]
    assert len(files_total_msg) == 1

    # Should have critical size alert (largest file way over 1-2 byte thresholds)
    size_critical_msg = [
        r
        for r in sys_results
        if isinstance(r, Result) and r.state == State.CRIT and "Largest:" in _get_text(r)
    ]
    assert len(size_critical_msg) == 1
    assert "warn/crit at 1 B/2 B" in size_critical_msg[0].summary


def test_check_filestats_additional_rules_regression_2_app_related_files(
    parsed: dict[str, tuple[str, list[dict[str, Any]]]],
) -> None:
    params = {
        "maxsize_largest": (4, 5),
        "additional_rules": [
            ("Sys-related files", "/var/log/sys*", {"maxsize_largest": (1, 2)}),
            ("", "/var/log/app*", {"maxsize_largest": (100, 200)}),
        ],
        "show_all_files": True,
    }

    result = list(check_filestats("foo", params, parsed))

    # Find app* pattern section
    app_pattern_results = [
        r
        for r in result
        if isinstance(r, Result) and "Pattern:" in _get_text(r) and "app*" in _get_text(r)
    ]
    assert len(app_pattern_results) == 1
    assert "'/var/log/app*'" in app_pattern_results[0].summary

    # Find the index of app pattern and check surrounding results
    app_pattern_index = None
    for i, result_obj in enumerate(result):
        if (
            isinstance(result_obj, Result)
            and "Pattern:" in _get_text(result_obj)
            and "app*" in _get_text(result_obj)
        ):
            app_pattern_index = i
            break

    assert app_pattern_index is not None

    # Check app-related files section
    app_results = result[app_pattern_index - 2 : app_pattern_index + 8]  # Include some context

    # Should find 1 app-related file (apport.log.2.gz)
    files_total_msg = [
        r for r in app_results if isinstance(r, Result) and "Files in total: 1" in _get_text(r)
    ]
    assert len(files_total_msg) == 1

    # Should have critical size alert (479 bytes over 100-200 byte thresholds)
    size_critical_msg = [
        r
        for r in app_results
        if isinstance(r, Result) and r.state == State.CRIT and "Largest:" in _get_text(r)
    ]
    assert len(size_critical_msg) == 1
    assert "warn/crit at 100 B/200 B" in size_critical_msg[0].summary


def test_check_filestats_additional_rules_regression_2_remaining_files(
    parsed: dict[str, tuple[str, list[dict[str, Any]]]],
) -> None:
    params = {
        "maxsize_largest": (4, 5),
        "additional_rules": [
            ("Sys-related files", "/var/log/sys*", {"maxsize_largest": (1, 2)}),
            ("", "/var/log/app*", {"maxsize_largest": (100, 200)}),
        ],
        "show_all_files": True,
    }

    result = list(check_filestats("foo", params, parsed))

    # Find remaining files message (should be 1 file: boot.log)
    remaining_msg = [
        r for r in result if isinstance(r, Result) and "Remaining files: 1" in _get_text(r)
    ]
    assert len(remaining_msg) == 1
    assert remaining_msg[0].state == State.OK

    # Find boot.log in remaining files section (now in details/notice)
    boot_log_msg = [
        r for r in result if isinstance(r, Result) and "/var/log/boot.log" in (r.details or "")
    ]
    assert len(boot_log_msg) == 1
    assert "142 kB" in boot_log_msg[0].details


def test_check_filestats_additional_rules_regression_2_file_details(
    parsed: dict[str, tuple[str, list[dict[str, Any]]]],
) -> None:
    params = {
        "maxsize_largest": (4, 5),
        "additional_rules": [
            ("Sys-related files", "/var/log/sys*", {"maxsize_largest": (1, 2)}),
            ("", "/var/log/app*", {"maxsize_largest": (100, 200)}),
        ],
        "show_all_files": True,
    }

    result = list(check_filestats("foo", params, parsed))

    # Check that detailed file information is included for sys-related files (in details/notice)
    sys_files_detail = [
        r
        for r in result
        if isinstance(r, Result)
        and "/var/log/syslog" in (r.details or "")
        and "Age:" in (r.details or "")
    ]
    assert len(sys_files_detail) == 1

    # Should contain multiple syslog files in the detail message
    detail_text = sys_files_detail[0].details
    assert "/var/log/syslog" in detail_text
    assert "/var/log/syslog.1" in detail_text
    assert "/var/log/syslog.3.gz" in detail_text
    assert "Age:" in detail_text
    assert "Size:" in detail_text


def test_check_filestats_additional_rules_regression_2_missing_item(
    parsed: dict[str, tuple[str, list[dict[str, Any]]]],
) -> None:
    result = list(check_filestats("NonExistent", {}, parsed))
    assert result == []
