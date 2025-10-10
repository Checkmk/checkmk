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
import time_machine

from cmk.base.legacy_checks.jolokia_jvm_runtime import (
    check_jolokia_jvm_runtime_uptime,
    discover_jolokia_jvm_runtime,
    parse_jolokia_jvm_runtime,
)


@pytest.fixture(name="string_table")
def _string_table() -> list[list[str]]:
    """
    Jolokia JVM Runtime data containing uptime information.
    Tests scenario with specific timestamp and uptime calculations.
    """
    return [
        [
            "MyJIRA",
            "java.lang:type=Runtime/Uptime,Name",
            '{"Uptime": 34502762, "Name": "1020@jira"}',
        ]
    ]


@pytest.fixture(name="parsed")
def _parsed(string_table: list[list[str]]) -> Mapping[str, Any]:
    return parse_jolokia_jvm_runtime(string_table)


def test_parse_jolokia_jvm_runtime(string_table: list[list[str]]) -> None:
    """Test parsing of JVM runtime data."""
    result = parse_jolokia_jvm_runtime(string_table)

    expected = {"MyJIRA": {"Uptime": 34502762, "Name": "1020@jira"}}

    assert result == expected


def test_discover_jolokia_jvm_runtime(parsed: Mapping[str, Any]) -> None:
    """Test discovery function for JVM runtime check."""
    result = list(discover_jolokia_jvm_runtime(parsed))
    assert result == [("MyJIRA", {})]


@time_machine.travel("2019-10-11 08:32:51")
def test_check_jolokia_jvm_runtime_uptime(parsed: Mapping[str, Any]) -> None:
    """Test uptime check with time mocking to ensure consistent results."""
    result = list(check_jolokia_jvm_runtime_uptime("MyJIRA", {}, parsed))

    assert len(result) == 1

    # Check uptime result
    uptime_result = result[0]
    assert uptime_result[0] == 0  # OK state
    assert "Up since" in uptime_result[1]
    assert "uptime: 9:35:02" in uptime_result[1]  # 34502.762 seconds = 9h 35m 2s

    # Check metrics
    assert len(uptime_result) == 3
    metrics = uptime_result[2]
    assert len(metrics) == 1
    uptime_metric = metrics[0]
    assert uptime_metric[0] == "uptime"
    assert uptime_metric[1] == pytest.approx(34502.762)


def test_check_jolokia_jvm_runtime_uptime_missing_item(parsed: Mapping[str, Any]) -> None:
    """Test check function with missing item."""
    result = list(check_jolokia_jvm_runtime_uptime("nonexistent", {}, parsed))
    assert result == []


def test_check_jolokia_jvm_runtime_uptime_missing_uptime_data() -> None:
    """Test check function with missing uptime data."""
    parsed_no_uptime = {
        "MyJIRA": {
            "Name": "1020@jira"
            # Missing "Uptime" field
        }
    }

    result = list(check_jolokia_jvm_runtime_uptime("MyJIRA", {}, parsed_no_uptime))
    assert result == []


@time_machine.travel("2019-10-11 08:32:51")
def test_check_jolokia_jvm_runtime_uptime_different_values() -> None:
    """Test uptime check with different uptime values."""
    test_cases = [
        (60000, "1:00:00"),  # 1 minute
        (3600000, "1:00:00:00"),  # 1 hour
        (86400000, "1 day"),  # 1 day
    ]

    for uptime_ms, expected_time_str in test_cases:
        parsed = {"TestInstance": {"Uptime": uptime_ms, "Name": "test@host"}}

        result = list(check_jolokia_jvm_runtime_uptime("TestInstance", {}, parsed))
        assert len(result) == 1
        assert result[0][0] == 0  # OK state
        assert "Up since" in result[0][1]

        # Verify metric value matches input
        metrics = result[0][2]
        assert metrics[0][1] == pytest.approx(uptime_ms / 1000.0)


@time_machine.travel("2019-10-11 08:32:51")
def test_jolokia_jvm_runtime_complete_workflow() -> None:
    """
    Comprehensive test for the complete JVM runtime workflow.
    Tests parse -> discover -> check pipeline with time mocking.
    """
    # Original string table from dataset
    string_table = [
        [
            "MyJIRA",
            "java.lang:type=Runtime/Uptime,Name",
            '{"Uptime": 34502762, "Name": "1020@jira"}',
        ]
    ]

    # Parse the data
    parsed = parse_jolokia_jvm_runtime(string_table)

    # Verify parsing
    assert "MyJIRA" in parsed
    assert parsed["MyJIRA"]["Uptime"] == 34502762
    assert parsed["MyJIRA"]["Name"] == "1020@jira"

    # Verify discovery
    discovery_result = list(discover_jolokia_jvm_runtime(parsed))
    assert discovery_result == [("MyJIRA", {})]

    # Verify check results match dataset expectations
    check_result = list(check_jolokia_jvm_runtime_uptime("MyJIRA", {}, parsed))
    assert len(check_result) == 1

    result = check_result[0]
    assert result[0] == 0  # OK state
    assert "Up since Thu Oct 10 22:57:48 2019" in result[1]  # Adjusted for timezone
    assert "uptime: 9:35:02" in result[1]

    # Verify metrics exactly match dataset expectations
    metrics = result[2]
    assert len(metrics) == 1
    assert metrics[0][0] == "uptime"  # metric name
    assert metrics[0][1] == 34502.762  # metric value
    # Other fields may vary based on uptime check implementation


def test_parse_jolokia_jvm_runtime_empty_data() -> None:
    """Test parsing with empty data."""
    result = parse_jolokia_jvm_runtime([])
    assert result == {}


def test_discover_jolokia_jvm_runtime_empty_section() -> None:
    """Test discovery with empty section."""
    result = list(discover_jolokia_jvm_runtime({}))
    assert result == []


def test_parse_jolokia_jvm_runtime_multiple_instances() -> None:
    """Test parsing with multiple JVM instances."""
    string_table = [
        [
            "JIRA1",
            "java.lang:type=Runtime/Uptime,Name",
            '{"Uptime": 1000000, "Name": "jira1@host"}',
        ],
        [
            "JIRA2",
            "java.lang:type=Runtime/Uptime,Name",
            '{"Uptime": 2000000, "Name": "jira2@host"}',
        ],
    ]

    result = parse_jolokia_jvm_runtime(string_table)

    assert len(result) == 2
    assert "JIRA1" in result
    assert "JIRA2" in result
    assert result["JIRA1"]["Uptime"] == 1000000
    assert result["JIRA2"]["Uptime"] == 2000000
