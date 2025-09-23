#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from cmk.base.legacy_checks.ups_socomec_in_voltage import (
    check_socomec_ups_in_voltage,
    inventory_socomec_ups_in_voltage,
    parse_ups_socomec_in_voltage,
)


def parsed() -> list[list[str]]:
    """Return parsed data from actual parse function."""
    return parse_ups_socomec_in_voltage([["1", "2300"]])


def test_ups_socomec_in_voltage_discovery():
    """Test discovery function finds voltage phases."""
    discovery_result = list(inventory_socomec_ups_in_voltage(parsed()))
    assert discovery_result == [("1", {})]


def test_ups_socomec_in_voltage_discovery_zero_voltage():
    """Test discovery ignores phases with zero voltage."""
    zero_data = parse_ups_socomec_in_voltage([["1", "0"]])
    discovery_result = list(inventory_socomec_ups_in_voltage(zero_data))
    assert discovery_result == []


def test_ups_socomec_in_voltage_check_ok():
    """Test voltage check with normal levels."""
    params = {"levels_lower": (210, 180)}
    state, summary, metrics = check_socomec_ups_in_voltage("1", params, parsed())
    assert state == 0
    assert "in voltage: 230V" in summary
    assert "(warn/crit at 210V/180V)" in summary
    assert metrics == [("in_voltage", 230, 210, 180, 150)]


def test_ups_socomec_in_voltage_check_warning():
    """Test voltage check with warning level triggered."""
    params = {"levels_lower": (240, 200)}
    state, summary, metrics = check_socomec_ups_in_voltage("1", params, parsed())
    assert state == 1
    assert "in voltage: 230V" in summary
    assert "(warn/crit at 240V/200V)" in summary
    assert metrics == [("in_voltage", 230, 240, 200, 150)]


def test_ups_socomec_in_voltage_check_critical():
    """Test voltage check with critical level triggered."""
    params = {"levels_lower": (250, 240)}
    state, summary, metrics = check_socomec_ups_in_voltage("1", params, parsed())
    assert state == 2
    assert "in voltage: 230V" in summary
    assert "(warn/crit at 250V/240V)" in summary
    assert metrics == [("in_voltage", 230, 250, 240, 150)]


def test_ups_socomec_in_voltage_check_missing_item():
    """Test voltage check with missing item returns unknown."""
    params = {"levels_lower": (210, 180)}
    result = check_socomec_ups_in_voltage("2", params, parsed())
    assert len(result) == 2  # Only state and summary, no metrics
    state, summary = result
    assert state == 3
    assert "Phase 2 not found in SNMP output" in summary


def test_ups_socomec_in_voltage_parse_function():
    """Test parse function handles SNMP data correctly."""
    raw_data = [["1", "2300"], ["2", "2250"]]
    parsed_result = parse_ups_socomec_in_voltage(raw_data)
    assert parsed_result == [["1", "2300"], ["2", "2250"]]
