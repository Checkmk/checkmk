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

from cmk.base.legacy_checks.ups_eaton_enviroment import (
    check_ups_eaton_enviroment,
    discover_ups_eaton_enviroment,
    parse_ups_eaton_enviroment,
)


@pytest.fixture(name="string_table")
def string_table_fixture() -> list[list[str]]:
    """Test data for UPS Eaton environment monitoring (temp, remote_temp, humidity)"""
    return [
        ["1", "40", "3"],  # temp=1°C, remote_temp=40°C, humidity=3%
    ]


@pytest.fixture(name="parsed")
def parsed_fixture(string_table: list[list[str]]) -> list[list[str]]:
    """Parsed UPS Eaton environment data"""
    return parse_ups_eaton_enviroment(string_table)


def test_discover_ups_eaton_enviroment(parsed: list[list[str]]) -> None:
    """Test environment discovery creates single service"""
    discovered = list(discover_ups_eaton_enviroment(parsed))
    assert len(discovered) == 1
    assert discovered[0][0] is None  # No item name
    assert discovered[0][1] == {}  # Empty parameters


def test_check_ups_eaton_enviroment_with_thresholds(parsed: list[list[str]]) -> None:
    """Test environment check with warning/critical thresholds"""
    params = {
        "temp": (40, 50),
        "remote_temp": (40, 50),
        "humidity": (65, 80),
    }

    result = list(check_ups_eaton_enviroment(None, params, parsed))

    # Should return 3 individual results for temp, remote_temp, humidity
    assert len(result) == 3

    # First result: temp=1, within thresholds (OK)
    assert result[0] == (0, "Temperature: 1.0 °C", [("temp", 1, 40, 50)])

    # Second result: remote_temp=40, hits warn threshold (WARN)
    assert result[1][0] == 1  # WARN state
    assert "Remote-Temperature: 40.0 °C" in result[1][1]
    assert "warn/crit at 40.0 °C/50.0 °C" in result[1][1]

    # Third result: humidity=3, within thresholds (OK)
    assert result[2] == (0, "Humidity: 3.0%", [("humidity", 3, 65, 80)])


def test_check_ups_eaton_enviroment_critical_state(parsed: list[list[str]]) -> None:
    """Test environment check with critical threshold breach"""
    # Set very low thresholds to trigger critical state
    params = {
        "temp": (0, 1),  # temp=1 hits critical
        "remote_temp": (30, 35),  # remote_temp=40 hits critical
        "humidity": (1, 2),  # humidity=3 hits critical
    }

    result = list(check_ups_eaton_enviroment(None, params, parsed))

    # Should return 3 individual results for temp, remote_temp, humidity
    assert len(result) == 3

    # First result: temp=1, hits critical threshold (CRIT)
    assert result[0][0] == 2  # CRIT state
    assert "Temperature: 1.0 °C" in result[0][1]
    assert "warn/crit at 0.0 °C/1.0 °C" in result[0][1]

    # Second result: remote_temp=40, hits critical threshold (CRIT)
    assert result[1][0] == 2  # CRIT state
    assert "Remote-Temperature: 40.0 °C" in result[1][1]
    assert "warn/crit at 30.0 °C/35.0 °C" in result[1][1]

    # Third result: humidity=3, hits critical threshold (CRIT)
    assert result[2][0] == 2  # CRIT state
    assert "Humidity: 3.0%" in result[2][1]
    assert "warn/crit at 1.0%/2.0%" in result[2][1]


def test_check_ups_eaton_enviroment_ok_state() -> None:
    """Test environment check with all values OK"""
    # Good values within thresholds
    good_data = [["25", "30", "50"]]  # temp=25°C, remote_temp=30°C, humidity=50%

    params = {
        "temp": (40, 50),
        "remote_temp": (40, 50),
        "humidity": (65, 80),
    }

    assert list(check_ups_eaton_enviroment(None, params, good_data)) == [
        (0, "Temperature: 25.0 °C", [("temp", 25, 40, 50)]),
        (0, "Remote-Temperature: 30.0 °C", [("remote_temp", 30, 40, 50)]),
        (0, "Humidity: 50.0%", [("humidity", 50, 65, 80)]),
    ]


def test_discover_ups_eaton_enviroment_empty_data() -> None:
    """Test discovery with empty data returns no services"""
    empty_data: list[list[str]] = []
    discovered = list(discover_ups_eaton_enviroment(empty_data))
    assert len(discovered) == 0


def test_parse_ups_eaton_enviroment(string_table: list[list[str]]) -> None:
    """Test that parsing returns the data unchanged"""
    parsed = parse_ups_eaton_enviroment(string_table)
    assert parsed == string_table
