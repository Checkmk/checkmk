#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

import pytest

from cmk.base.check_legacy_includes.dell_poweredge import check_dell_poweredge_temp
from cmk.base.legacy_checks.dell_poweredge_temp import (
    discover_dell_poweredge_temp,
    parse_dell_poweredge_temp,
)


@pytest.fixture(name="string_table")
def string_table_fixture() -> list[list[str]]:
    """Test data for Dell PowerEdge temperature sensors"""
    return [
        ["1", "1", "2", "3", "170", "System Board Inlet Temp", "470", "420", "30", "-70"],
        ["1", "2", "2", "3", "300", "System Board Exhaust Temp", "750", "700", "80", "30"],
        ["1", "3", "1", "2", "", "CPU1 Temp", "", "", "", ""],
        ["1", "4", "1", "2", "", "CPU2 Temp", "", "", "", ""],
    ]


@pytest.fixture(name="parsed")
def parsed_fixture(string_table: list[list[str]]) -> list[list[str]]:
    """Parsed Dell PowerEdge temperature data"""
    return parse_dell_poweredge_temp(string_table)


def test_parse_dell_poweredge_temp(string_table: list[list[str]]) -> None:
    """Test Dell PowerEdge temperature parsing (passthrough)"""
    parsed = parse_dell_poweredge_temp(string_table)
    assert parsed == string_table  # Parse function is passthrough


def test_discover_dell_poweredge_temp(parsed: list[list[str]]) -> None:
    """Test Dell PowerEdge temperature discovery"""
    discovered = list(discover_dell_poweredge_temp(parsed))

    # Should discover 2 sensors (ones with StateSettings != "1")
    assert len(discovered) == 2

    # Check discovered items (names are trimmed of " Temp" suffix)
    discovered_items = [item[0] for item in discovered]
    assert "System Board Inlet" in discovered_items
    assert "System Board Exhaust" in discovered_items

    # Parameters should be empty
    for item, params in discovered:
        assert params == {}


def test_discover_dell_poweredge_temp_filters_unknown_state() -> None:
    """Test that sensors with StateSettings = '1' (unknown) are filtered out"""
    test_data = [
        [
            "1",
            "1",
            "1",
            "3",
            "170",
            "Unknown Sensor",
            "470",
            "420",
            "30",
            "-70",
        ],  # StateSettings = 1
        ["1", "2", "2", "3", "300", "Good Sensor", "750", "700", "80", "30"],  # StateSettings = 2
    ]

    discovered = list(discover_dell_poweredge_temp(test_data))

    # Should only discover the sensor with StateSettings = 2
    assert len(discovered) == 1
    assert discovered[0][0] == "Good Sensor"


def test_check_dell_poweredge_temp_inlet_normal(parsed: list[list[str]]) -> None:
    """Test Dell PowerEdge temperature check for System Board Inlet in normal state"""
    item = "System Board Inlet"

    result = list(check_dell_poweredge_temp(item, {}, parsed))

    # Should have temperature check result
    assert len(result) >= 1

    # Check temperature value (170 / 10.0 = 17.0°C)
    temp_result = None
    for check_result in result:
        if len(check_result) == 3 and check_result[2]:  # Has performance data
            temp_result = check_result
            break

    assert temp_result is not None
    assert temp_result[0] == 0  # OK state
    assert "17.0" in temp_result[1]  # Temperature value

    # Check performance data
    perf_data = temp_result[2]
    assert len(perf_data) == 1
    assert perf_data[0][0] == "temp"
    assert perf_data[0][1] == 17.0  # Temperature value
    assert perf_data[0][2] == 42.0  # Warning threshold (420 / 10)
    assert perf_data[0][3] == 47.0  # Critical threshold (470 / 10)


def test_check_dell_poweredge_temp_exhaust_normal(parsed: list[list[str]]) -> None:
    """Test Dell PowerEdge temperature check for System Board Exhaust in normal state"""
    item = "System Board Exhaust"

    result = list(check_dell_poweredge_temp(item, {}, parsed))

    # Should have temperature check result
    assert len(result) >= 1

    # Check temperature value (300 / 10.0 = 30.0°C)
    temp_result = None
    for check_result in result:
        if len(check_result) == 3 and check_result[2]:  # Has performance data
            temp_result = check_result
            break

    assert temp_result is not None
    assert temp_result[0] == 0  # OK state
    assert "30.0" in temp_result[1]  # Temperature value

    # Check performance data
    perf_data = temp_result[2]
    assert len(perf_data) == 1
    assert perf_data[0][0] == "temp"
    assert perf_data[0][1] == 30.0  # Temperature value
    assert perf_data[0][2] == 70.0  # Warning threshold (700 / 10)
    assert perf_data[0][3] == 75.0  # Critical threshold (750 / 10)


def test_check_dell_poweredge_temp_missing_reading() -> None:
    """Test Dell PowerEdge temperature check when reading is missing"""
    test_data = [
        ["1", "3", "2", "3", "", "CPU1 Temp", "", "", "", ""],  # No reading
    ]

    item = "CPU1"
    result = list(check_dell_poweredge_temp(item, {}, test_data))

    # Should return no results for missing reading
    assert len(result) == 0


def test_check_dell_poweredge_temp_nonexistent_item(parsed: list[list[str]]) -> None:
    """Test Dell PowerEdge temperature check for non-existent item"""
    item = "Nonexistent Sensor"
    result = list(check_dell_poweredge_temp(item, {}, parsed))

    # Should return no results for non-existent item
    assert len(result) == 0


def test_check_dell_poweredge_temp_with_thresholds() -> None:
    """Test Dell PowerEdge temperature check with various threshold conditions"""
    # Test data with different status values
    test_data = [
        [
            "1",
            "1",
            "2",
            "4",
            "800",
            "Hot Sensor",
            "700",
            "600",
            "200",
            "100",
        ],  # nonCriticalUpper (warning)
        [
            "1",
            "2",
            "2",
            "5",
            "900",
            "Critical Sensor",
            "700",
            "600",
            "200",
            "100",
        ],  # CriticalUpper (critical)
        ["1", "3", "2", "3", "300", "Normal Sensor", "700", "600", "200", "100"],  # Normal
    ]

    # Test warning state
    result_warn = list(check_dell_poweredge_temp("Hot Sensor", {}, test_data))
    assert len(result_warn) >= 1
    # Should have a warning state result
    warning_found = any(check_result[0] == 1 for check_result in result_warn)
    assert warning_found

    # Test critical state
    result_crit = list(check_dell_poweredge_temp("Critical Sensor", {}, test_data))
    assert len(result_crit) >= 1
    # Should have a critical state result
    critical_found = any(check_result[0] == 2 for check_result in result_crit)
    assert critical_found

    # Test normal state
    result_ok = list(check_dell_poweredge_temp("Normal Sensor", {}, test_data))
    # Should not have any non-OK temperature states (status 3 = OK)
    temp_states = [check_result[0] for check_result in result_ok if len(check_result) == 3]
    if temp_states:
        # Temperature result should be OK
        assert 0 in temp_states


def test_check_dell_poweredge_temp_item_name_trimming() -> None:
    """Test that item names are correctly trimmed of ' Temp' suffix"""
    test_data = [
        ["1", "1", "2", "3", "250", "Processor 1 Temp", "700", "600", "200", "100"],
        ["1", "2", "2", "3", "280", "Memory Module", "700", "600", "200", "100"],
    ]

    discovered = list(discover_dell_poweredge_temp(test_data))

    # Should discover 2 items with trimmed names
    assert len(discovered) == 2
    discovered_items = [item[0] for item in discovered]

    # "Processor 1 Temp" should become "Processor 1"
    assert "Processor 1" in discovered_items
    # "Memory Module" should stay "Memory Module" (no " Temp" suffix)
    assert "Memory Module" in discovered_items


def test_check_dell_poweredge_temp_no_thresholds() -> None:
    """Test Dell PowerEdge temperature check with missing threshold values"""
    test_data = [
        ["1", "1", "2", "3", "250", "No Threshold Sensor", "", "", "", ""],
    ]

    item = "No Threshold Sensor"
    result = list(check_dell_poweredge_temp(item, {}, test_data))

    # Should still work but with no device thresholds
    assert len(result) >= 1

    # Check that temperature reading works
    temp_result = None
    for check_result in result:
        if len(check_result) == 3 and check_result[2]:  # Has performance data
            temp_result = check_result
            break

    assert temp_result is not None
    assert temp_result[0] == 0  # OK state
    assert "25.0" in temp_result[1]  # Temperature value (250 / 10)


def test_check_dell_poweredge_temp_edge_case_fallback_naming() -> None:
    """Test item naming when LocationName is empty"""
    test_data = [
        ["2", "5", "2", "3", "350", "", "700", "600", "200", "100"],  # Empty LocationName
    ]

    discovered = list(discover_dell_poweredge_temp(test_data))

    # Should use chassisIndex-Index format when LocationName is empty
    assert len(discovered) == 1
    assert discovered[0][0] == "2-5"
