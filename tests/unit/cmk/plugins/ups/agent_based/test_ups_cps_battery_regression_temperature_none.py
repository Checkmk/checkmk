#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.ups.agent_based.ups_cps_battery import (
    check_ups_cps_battery,
    check_ups_cps_battery_temp,
    discover_ups_cps_battery,
    discover_ups_cps_battery_temp,
    parse_ups_cps_battery,
    Section,
)


@pytest.fixture(name="string_table")
def fixture_string_table() -> list[list[str]]:
    """Test data with temperature set to NULL.

    Data format: [capacity%, temperature, battery_time_ticks]
    - 100: Battery capacity percentage
    - NULL: Temperature reading unavailable
    - 612000: Battery runtime in ticks (1/100 seconds)
    """
    return [["100", "NULL", "612000"]]


@pytest.fixture(name="parsed_data")
def fixture_parsed_data(string_table: list[list[str]]) -> Section | None:
    """Parsed UPS battery data with temperature unavailable."""
    return parse_ups_cps_battery(string_table)


def test_parse_ups_cps_battery_temperature_none(string_table: list[list[str]]) -> None:
    """Test parsing when temperature is NULL."""
    parsed = parse_ups_cps_battery(string_table)

    assert parsed is not None
    assert parsed["capacity"] == 100
    assert parsed["battime"] == 6120.0  # 612000 / 100
    assert "temperature" not in parsed  # Should not be present when NULL


def test_parse_ups_cps_battery_empty_data() -> None:
    """Test parsing with empty string table."""
    assert parse_ups_cps_battery([]) is None


def test_discover_ups_cps_battery_temperature_none(parsed_data: Section | None) -> None:
    """Test temperature discovery when temperature unavailable."""
    # No temperature data available, no services discovered
    assert list(discover_ups_cps_battery_temp(parsed_data)) == []


def test_discover_ups_cps_battery_capacity(parsed_data: Section | None) -> None:
    """Test capacity service discovery."""
    assert list(discover_ups_cps_battery(parsed_data)) == [Service()]


def test_check_ups_cps_battery_temperature_none(parsed_data: Section | None) -> None:
    """Test temperature check when temperature unavailable yields nothing."""
    assert list(check_ups_cps_battery_temp("Battery", {}, parsed_data)) == []


@pytest.mark.parametrize(
    "params, expected_capacity_status, expected_battime_status",
    [
        # Default parameters - all OK (100% capacity > 95 warn, 90 crit)
        ({"capacity": (95, 90)}, State.OK, State.OK),
        # Equal to warning threshold (100% capacity = 100 warn, 95 crit)
        ({"capacity": (100, 95)}, State.OK, State.OK),
        # Below warning threshold (100% capacity < 105 warn, 100 crit)
        ({"capacity": (105, 100)}, State.WARN, State.OK),
        # With battery time thresholds (102 min > 100 warn, 90 crit)
        ({"capacity": (95, 90), "battime": (100, 90)}, State.OK, State.OK),
        # Battery time critical (102 min < 110 warn, 105 crit)
        ({"capacity": (95, 90), "battime": (110, 105)}, State.OK, State.CRIT),
        # Battery time critical (102 min < 105 warn, 103 crit)
        ({"capacity": (95, 90), "battime": (105, 103)}, State.OK, State.CRIT),
    ],
)
def test_check_ups_cps_battery_capacity_and_time(
    parsed_data: Section | None,
    params: Mapping[str, object],
    expected_capacity_status: State,
    expected_battime_status: State,
) -> None:
    """Test UPS battery capacity and runtime checks with various thresholds."""
    results = [r for r in check_ups_cps_battery(params, parsed_data) if isinstance(r, Result)]

    assert len(results) == 2

    # First result: capacity check
    assert results[0].state == expected_capacity_status
    assert "Capacity at 100%" in results[0].summary

    # Second result: battery time check
    assert results[1].state == expected_battime_status
    assert "102 minutes remaining on battery" in results[1].summary
