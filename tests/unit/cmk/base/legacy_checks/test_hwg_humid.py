#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from typing import Any

from cmk.agent_based.v2 import StringTable
from cmk.base.check_legacy_includes.hwg import parse_hwg
from cmk.base.legacy_checks.hwg_humidity import (
    check_hwg_humidity,
    discover_hwg_humidity,
)


def test_discover_hwg_humidity_basic() -> None:
    """Test inventory function for hwg_humidity check with basic data."""
    string_table: StringTable = [
        ["1", "Sensor 1", "2", "45.5", "4"],  # humidity sensor (%=unit 4)
        ["2", "Sensor 2", "2", "55.2", "4"],  # humidity sensor (%=unit 4)
        ["3", "Temp Sensor", "2", "23.5", "1"],  # temperature sensor (°C=unit 1)
    ]

    parsed = parse_hwg(string_table)
    result = list(discover_hwg_humidity(parsed))

    # Should discover humidity sensors (index 1 and 2), but not temperature (index 3)
    assert sorted(result) == [("1", {}), ("2", {})]


def test_check_hwg_humidity_normal_levels() -> None:
    """Test check function for hwg_humidity with normal humidity levels."""
    string_table: StringTable = [
        ["1", "Office Humidity", "2", "45.5", "4"],  # normal level
    ]

    parsed = parse_hwg(string_table)
    params: dict[str, Any] = {"levels": (60.0, 70.0)}

    result = list(check_hwg_humidity("1", params, parsed))

    # Should return one result
    assert len(result) == 2

    state, summary, perfdata = result[0]

    # 45.5% is below warning level (60%), so should be OK
    assert state == 0
    assert "45.5" in summary
    # Should have performance data
    assert perfdata

    state, summary = result[1]
    assert "Office Humidity" in summary
    assert "Status:" in summary


def test_check_hwg_humidity_warning_level() -> None:
    """Test check function for hwg_humidity at warning level."""
    string_table: StringTable = [
        ["2", "Warehouse Humidity", "2", "65.0", "4"],  # warning level
    ]

    parsed = parse_hwg(string_table)
    params: dict[str, Any] = {"levels": (60.0, 70.0)}

    result = list(check_hwg_humidity("2", params, parsed))

    # Should return one result
    assert len(result) == 2

    state, summary, perfdata = result[0]

    # 65% is above warning (60%) but below critical (70%), so should be WARNING
    assert state == 1
    assert "65.0" in summary
    # Should have performance data
    assert perfdata

    state, summary = result[1]
    assert "Warehouse Humidity" in summary


def test_check_hwg_humidity_critical_level() -> None:
    """Test check function for hwg_humidity at critical level."""
    string_table: StringTable = [
        ["3", "Server Room", "2", "75.0", "4"],  # critical level
    ]

    parsed = parse_hwg(string_table)
    params: dict[str, Any] = {"levels": (60.0, 70.0)}

    result = list(check_hwg_humidity("3", params, parsed))

    # Should return one result
    assert len(result) == 2

    state, summary, perfdata = result[0]

    # 75% is above critical (70%), so should be CRITICAL
    assert state == 2
    assert "75.0" in summary
    # Should have performance data
    assert perfdata is not None

    state, summary = result[1]
    assert "Server Room" in summary


def test_check_hwg_humidity_device_status() -> None:
    """Test check function for hwg_humidity includes device status information."""
    string_table: StringTable = [
        ["1", "Test Sensor", "3", "50.0", "4"],  # status 3 = "alarm low"
    ]

    parsed = parse_hwg(string_table)
    params: dict[str, Any] = {"levels": (60.0, 70.0)}

    result = list(check_hwg_humidity("1", params, parsed))

    # Should return one result
    assert len(result) == 2

    state, summary = result[1]
    # Should include device status in summary
    assert "Test Sensor" in summary
    assert "Status:" in summary


def test_check_hwg_humidity_missing_item() -> None:
    """Test check function for hwg_humidity with missing sensor."""
    string_table: StringTable = [
        ["1", "Existing Sensor", "2", "45.0", "4"],
    ]

    parsed = parse_hwg(string_table)
    params: dict[str, Any] = {"levels": (60.0, 70.0)}

    # Try to check a sensor that doesn't exist
    result = list(check_hwg_humidity("999", params, parsed))

    # Should return empty (no results for missing sensor)
    assert result == []
