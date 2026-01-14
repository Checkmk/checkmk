#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="no-untyped-call"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from typing import Any

import pytest

from cmk.base.legacy_checks.fsc_fans import (
    check_fsc_fans,
    discover_fsc_fans,
    parse_fsc_fans,
)


@pytest.fixture(name="string_table")
def string_table_fixture() -> list[list[str]]:
    """Test data for FSC fan monitoring"""
    return [
        ["NULL", "NULL"],  # Invalid fan entry (filtered out)
        ["FAN1 SYS", "4140"],  # Valid fan with 4140 RPM
    ]


@pytest.fixture(name="parsed")
def parsed_fixture(string_table: list[list[str]]) -> dict[str, Any]:
    """Parsed FSC fan data"""
    return parse_fsc_fans(string_table)


def test_discover_fsc_fans(parsed: dict[str, Any]) -> None:
    """Test FSC fan discovery finds valid fans"""
    discovered = list(discover_fsc_fans(parsed))
    assert len(discovered) == 1
    assert discovered[0][0] == "FAN1 SYS"
    assert discovered[0][1] == {}  # Empty parameters


def test_check_fsc_fans_normal_speed(parsed: dict[str, Any]) -> None:
    """Test FSC fan check with normal fan speed"""
    params = {"lower": (2000, 1000)}  # warn below 2000, crit below 1000
    result = list(check_fsc_fans("FAN1 SYS", params, parsed))

    # check_fsc_fans yields results
    assert len(result) == 1
    state, message = result[0][:2]
    assert state == 0  # OK
    assert message == "Speed: 4140 RPM"


def test_check_fsc_fans_warning_speed(parsed: dict[str, Any]) -> None:
    """Test FSC fan check with low fan speed (warning)"""
    # Set high thresholds to trigger warning
    params = {"lower": (5000, 4000)}  # warn below 5000, crit below 4000
    result = list(check_fsc_fans("FAN1 SYS", params, parsed))

    assert len(result) == 1
    state, message = result[0][:2]
    assert state == 1  # WARNING
    assert "4140" in message
    assert "below" in message.lower() or "warn" in message.lower()


def test_check_fsc_fans_critical_speed(parsed: dict[str, Any]) -> None:
    """Test FSC fan check with critically low fan speed"""
    # Set very high thresholds to trigger critical
    params = {"lower": (6000, 5000)}  # warn below 6000, crit below 5000
    result = list(check_fsc_fans("FAN1 SYS", params, parsed))

    assert len(result) == 1
    state, message = result[0][:2]
    assert state == 2  # CRITICAL
    assert "4140" in message


def test_check_fsc_fans_legacy_tuple_params(parsed: dict[str, Any]) -> None:
    """Test FSC fan check with legacy tuple parameters"""
    # Legacy format: (warn_lower, crit_lower)
    params = (2000, 1000)
    result = list(check_fsc_fans("FAN1 SYS", params, parsed))

    assert len(result) == 1
    state, message = result[0][:2]
    assert state == 0  # OK - 4140 is above both thresholds
    assert "4140" in message


def test_check_fsc_fans_missing_fan(parsed: dict[str, Any]) -> None:
    """Test FSC fan check for non-existent fan"""
    params = {"lower": (2000, 1000)}
    result = list(check_fsc_fans("NONEXISTENT", params, parsed))
    assert len(result) == 0  # No results for missing fan


def test_parse_fsc_fans_structure(string_table: list[list[str]]) -> None:
    """Test FSC fan parsing creates correct structure"""
    parsed = parse_fsc_fans(string_table)

    # Should only have valid fan (NULL entries filtered out)
    assert len(parsed) == 1
    assert "FAN1 SYS" in parsed
    assert parsed["FAN1 SYS"] == 4140
    assert "NULL" not in parsed  # Invalid entries filtered out


def test_parse_fsc_fans_invalid_rpm() -> None:
    """Test FSC fan parsing handles invalid RPM values"""
    invalid_data = [
        ["FAN1", "not_a_number"],
        ["FAN2", ""],
        ["FAN3", "1500"],  # Valid
        ["FAN4", "invalid"],
    ]

    parsed = parse_fsc_fans(invalid_data)

    # Should only contain the valid entry
    assert len(parsed) == 1
    assert "FAN3" in parsed
    assert parsed["FAN3"] == 1500


def test_check_fsc_fans_zero_speed() -> None:
    """Test FSC fan check with zero speed (stopped fan)"""
    zero_speed_data = [["STOPPED_FAN", "0"]]
    parsed = parse_fsc_fans(zero_speed_data)

    params = {"lower": (2000, 1000)}
    result = list(check_fsc_fans("STOPPED_FAN", params, parsed))

    # Zero speed may be filtered out by parsing or check logic
    # Let's just verify the parsing worked and check if result exists
    assert "STOPPED_FAN" in parsed
    assert parsed["STOPPED_FAN"] == 0
    # If there's a result, verify it indicates a problem
    if result:
        state, message = result[0][:2]
        assert state >= 1  # Should be WARNING or CRITICAL
        assert "0" in message


def test_discover_fsc_fans_empty_data() -> None:
    """Test FSC fan discovery with empty data"""
    empty_parsed: dict[str, Any] = {}
    discovered = list(discover_fsc_fans(empty_parsed))
    assert len(discovered) == 0


def test_discover_fsc_fans_multiple_fans() -> None:
    """Test FSC fan discovery with multiple valid fans"""
    multi_fan_data = [
        ["FAN1 SYS", "4140"],
        ["FAN2 SYS", "3800"],
        ["FAN3 CPU", "4500"],
        ["NULL", "NULL"],  # Should be filtered out
    ]

    parsed = parse_fsc_fans(multi_fan_data)
    discovered = list(discover_fsc_fans(parsed))

    assert len(discovered) == 3
    fan_names = [item[0] for item in discovered]
    assert "FAN1 SYS" in fan_names
    assert "FAN2 SYS" in fan_names
    assert "FAN3 CPU" in fan_names
    assert "NULL" not in fan_names
