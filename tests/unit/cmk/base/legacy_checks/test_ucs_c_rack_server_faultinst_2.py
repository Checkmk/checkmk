#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

import pytest

from cmk.base.legacy_checks.ucs_c_rack_server_faultinst import (
    check_ucs_c_rack_server_faultinst,
    discover_ucs_c_rack_server_faultinst,
)
from cmk.plugins.collection.agent_based.ucs_c_rack_server_faultinst import (
    parse_ucs_c_rack_server_faultinst,
)


@pytest.fixture(name="string_table")
def fixture_string_table() -> list[list[str]]:
    """UCS rack server fault instance data with different severity levels.

    Tests all possible severity states and their mapping to monitoring states:
    - info, condition, cleared -> OK (0)
    - minor, warning, major -> WARNING (1)
    - critical -> CRITICAL (2)
    - unknown -> UNKNOWN (3)
    """
    return [
        [
            "faultInst",
            "severity info",
            "cause powerproblem",
            "code F0883",
            "descr Broken",
            "affectedDN sys/rack-unit-1/psu-4",
        ],
        [
            "faultInst",
            "severity condition",
            "cause powerproblem",
            "code F0883",
            "descr Broken",
            "affectedDN sys/rack-unit-1/psu-4",
        ],
        [
            "faultInst",
            "severity cleared",
            "cause powerproblem",
            "code F0883",
            "descr Broken",
            "affectedDN sys/rack-unit-1/psu-4",
        ],
        [
            "faultInst",
            "severity minor",
            "cause powerproblem",
            "code F0883",
            "descr Broken",
            "affectedDN sys/rack-unit-1/psu-4",
        ],
        [
            "faultInst",
            "severity warning",
            "cause powerproblem",
            "code F0883",
            "descr Broken",
            "affectedDN sys/rack-unit-1/psu-4",
        ],
        [
            "faultInst",
            "severity major",
            "cause powerproblem",
            "code F0883",
            "descr Broken",
            "affectedDN sys/rack-unit-1/psu-4",
        ],
        [
            "faultInst",
            "severity critical",
            "cause powerproblem",
            "code F0883",
            "descr Broken",
            "affectedDN sys/rack-unit-1/psu-4",
        ],
        [
            "faultInst",
            "severity unknown",
            "cause powerproblem",
            "code F0883",
            "descr Broken",
            "affectedDN sys/rack-unit-1/psu-4",
        ],
    ]


@pytest.fixture(name="parsed_data")
def fixture_parsed_data(string_table: list[list[str]]) -> dict[str, list[str]]:
    """Parsed UCS fault instance data."""
    return parse_ucs_c_rack_server_faultinst(string_table)


def test_parse_ucs_c_rack_server_faultinst_multiple_severities(
    string_table: list[list[str]],
) -> None:
    """Test parsing UCS fault instances with multiple severity levels."""
    parsed = parse_ucs_c_rack_server_faultinst(string_table)

    assert len(parsed["Severity"]) == 8
    expected_severities = [
        "info",
        "condition",
        "cleared",
        "minor",
        "warning",
        "major",
        "critical",
        "unknown",
    ]
    assert parsed["Severity"] == expected_severities

    # All should have same cause, code, description
    assert all(cause == "powerproblem" for cause in parsed["Cause"])
    assert all(code == "F0883" for code in parsed["Code"])
    assert all(desc == "Broken" for desc in parsed["Description"])

    # Affected DN should have sys/ prefix removed
    assert all(dn == "rack-unit-1/psu-4" for dn in parsed["Affected DN"])


def test_parse_ucs_c_rack_server_faultinst_empty_data() -> None:
    """Test parsing with empty data."""
    parsed = parse_ucs_c_rack_server_faultinst([])
    assert parsed == {}


def test_parse_ucs_c_rack_server_faultinst_single_fault() -> None:
    """Test parsing with single fault instance."""
    string_table = [
        [
            "faultInst",
            "severity critical",
            "cause powerproblem",
            "code F0883",
            "descr Power supply failure",
            "affectedDN sys/rack-unit-1/psu-2",
        ]
    ]

    parsed = parse_ucs_c_rack_server_faultinst(string_table)

    assert parsed["Severity"] == ["critical"]
    assert parsed["Cause"] == ["powerproblem"]
    assert parsed["Code"] == ["F0883"]
    assert parsed["Description"] == ["Power supply failure"]
    assert parsed["Affected DN"] == ["rack-unit-1/psu-2"]


def test_discover_ucs_c_rack_server_faultinst(parsed_data: dict[str, list[str]]) -> None:
    """Test discovery of UCS fault instance service."""
    items = list(discover_ucs_c_rack_server_faultinst(parsed_data))

    assert len(items) == 1
    assert items[0] == (None, {})


def test_discover_ucs_c_rack_server_faultinst_empty_data() -> None:
    """Test discovery with empty data."""
    items = list(discover_ucs_c_rack_server_faultinst({}))

    assert len(items) == 1
    assert items[0] == (None, {})


def test_check_ucs_c_rack_server_faultinst_multiple_severities(
    parsed_data: dict[str, list[str]],
) -> None:
    """Test check function with multiple fault severities."""
    results = list(check_ucs_c_rack_server_faultinst(None, {}, parsed_data))

    # Should have 9 results: 1 summary + 8 individual faults
    assert len(results) == 9

    # First result should be the summary with CRITICAL status (highest severity)
    summary_result = results[0]
    assert summary_result[0] == 2  # CRITICAL state
    assert "Found faults:" in summary_result[1]
    assert "1 with severity 'cleared'" in summary_result[1]
    assert "1 with severity 'condition'" in summary_result[1]
    assert "1 with severity 'critical'" in summary_result[1]
    assert "1 with severity 'info'" in summary_result[1]
    assert "1 with severity 'major'" in summary_result[1]
    assert "1 with severity 'minor'" in summary_result[1]
    assert "1 with severity 'unknown'" in summary_result[1]
    assert "1 with severity 'warning'" in summary_result[1]

    # Individual fault results should be sorted by monitoring state
    individual_results = results[1:]

    # Check expected monitoring states for each severity
    expected_states = [0, 0, 0, 1, 1, 1, 2, 3]  # Sorted by state priority
    for i, result in enumerate(individual_results):
        assert result[0] == expected_states[i]
        assert "Severity:" in result[1]
        assert "Description: Broken" in result[1]
        assert "Cause: powerproblem" in result[1]
        assert "Code: F0883" in result[1]
        assert "Affected DN: rack-unit-1/psu-4" in result[1]


def test_check_ucs_c_rack_server_faultinst_empty_data() -> None:
    """Test check function with no fault instances."""
    results = list(check_ucs_c_rack_server_faultinst(None, {}, {}))

    assert len(results) == 1
    assert results[0] == (0, "No fault instances found")


def test_check_ucs_c_rack_server_faultinst_only_warnings() -> None:
    """Test check function with only warning-level faults."""
    parsed_data = {
        "Severity": ["minor", "warning"],
        "Cause": ["powerproblem", "powerproblem"],
        "Code": ["F0883", "F0883"],
        "Description": ["Issue 1", "Issue 2"],
        "Affected DN": ["rack-unit-1/psu-1", "rack-unit-1/psu-2"],
    }

    results = list(check_ucs_c_rack_server_faultinst(None, {}, parsed_data))

    # Should have 3 results: 1 summary + 2 individual faults
    assert len(results) == 3

    # Summary should be WARNING (max of minor/warning severities)
    assert results[0][0] == 1  # WARNING state
    assert "Found faults:" in results[0][1]
    assert "1 with severity 'minor'" in results[0][1]
    assert "1 with severity 'warning'" in results[0][1]


def test_check_ucs_c_rack_server_faultinst_critical_present() -> None:
    """Test check function prioritizes critical faults in overall state."""
    parsed_data = {
        "Severity": ["info", "critical", "warning"],
        "Cause": ["cause1", "cause2", "cause3"],
        "Code": ["F001", "F002", "F003"],
        "Description": ["Info fault", "Critical fault", "Warning fault"],
        "Affected DN": ["dn1", "dn2", "dn3"],
    }

    results = list(check_ucs_c_rack_server_faultinst(None, {}, parsed_data))

    # Summary should be CRITICAL even though other severities are present
    assert results[0][0] == 2  # CRITICAL state
    assert "Found faults:" in results[0][1]
