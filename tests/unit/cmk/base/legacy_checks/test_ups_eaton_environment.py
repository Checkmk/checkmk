#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.


import pytest

from cmk.base.legacy_checks.ups_eaton_enviroment import (
    check_ups_eaton_enviroment,
    inventory_ups_eaton_enviroment,
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


def test_inventory_ups_eaton_enviroment(parsed: list[list[str]]) -> None:
    """Test environment discovery creates single service"""
    discovered = list(inventory_ups_eaton_enviroment(parsed))
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

    result = check_ups_eaton_enviroment(None, params, parsed)

    # Should return tuple (state, summary, metrics)
    assert len(result) == 3
    state, summary, metrics = result

    # Overall state should be WARN (1) because remote_temp hits warn threshold
    assert state == 1

    # Check summary contains all three measurements
    assert "Temperature: 1 °C" in summary
    assert "Remote-Temperature: 40 °C" in summary
    assert "Humidity: 3%" in summary

    # Check that remote_temp warning is indicated
    assert "Remote-Temperature: 40 °C (warn/crit at 40 °C/50 °C)(!)" in summary

    # Check metrics format
    assert len(metrics) == 3
    temp_metric, remote_temp_metric, humidity_metric = metrics

    # temp metric: value=1, warn=40, crit=50
    assert temp_metric == ("temp", 1, 40, 50)

    # remote_temp metric: value=40, warn=40, crit=50 (hits warning)
    assert remote_temp_metric == ("remote_temp", 40, 40, 50)

    # humidity metric: value=3, warn=65, crit=80
    assert humidity_metric == ("humidity", 3, 65, 80)


def test_check_ups_eaton_enviroment_critical_state(parsed: list[list[str]]) -> None:
    """Test environment check with critical threshold breach"""
    # Set very low thresholds to trigger critical state
    params = {
        "temp": (0, 1),  # temp=1 hits critical
        "remote_temp": (30, 35),  # remote_temp=40 hits critical
        "humidity": (1, 2),  # humidity=3 hits critical
    }

    result = check_ups_eaton_enviroment(None, params, parsed)
    state, summary, metrics = result

    # Should be CRITICAL (2) due to multiple breaches
    assert state == 2

    # Check that critical indicators are present
    assert "Temperature: 1 °C (warn/crit at 0 °C/1 °C)(!!)" in summary
    assert "Remote-Temperature: 40 °C (warn/crit at 30 °C/35 °C)(!!)" in summary
    assert "Humidity: 3% (warn/crit at 1%/2%)(!!)" in summary


def test_check_ups_eaton_enviroment_ok_state() -> None:
    """Test environment check with all values OK"""
    # Good values within thresholds
    good_data = [["25", "30", "50"]]  # temp=25°C, remote_temp=30°C, humidity=50%

    params = {
        "temp": (40, 50),
        "remote_temp": (40, 50),
        "humidity": (65, 80),
    }

    result = check_ups_eaton_enviroment(None, params, good_data)
    state, summary, metrics = result

    # Should be OK (0)
    assert state == 0

    # No warning/critical indicators
    assert "(!)" not in summary
    assert "(!!)" not in summary

    # Check values in summary
    assert "Temperature: 25 °C" in summary
    assert "Remote-Temperature: 30 °C" in summary
    assert "Humidity: 50%" in summary


def test_inventory_ups_eaton_enviroment_empty_data() -> None:
    """Test discovery with empty data returns no services"""
    empty_data: list[list[str]] = []
    discovered = list(inventory_ups_eaton_enviroment(empty_data))
    assert len(discovered) == 0


def test_parse_ups_eaton_enviroment(string_table: list[list[str]]) -> None:
    """Test that parsing returns the data unchanged"""
    parsed = parse_ups_eaton_enviroment(string_table)
    assert parsed == string_table
