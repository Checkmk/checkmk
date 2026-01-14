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

from cmk.base.legacy_checks.carel_sensors import (
    carel_sensors_parse,
    check_carel_sensors_temp,
    discover_carel_sensors_temp,
)


def parsed() -> Mapping[str, object]:
    """Test parsing of SNMP data for carel_sensors."""
    string_table = [
        ["1.0", "264"],  # Room = 26.4°C
        ["2.0", "0"],  # Outdoor = 0 (filtered out)
        ["3.0", "221"],  # Delivery = 22.1°C
        ["20.0", "220"],  # Cooling Set Point = 22.0°C
        ["21.0", "150"],  # Cooling Prop. Band = 15.0°C
        ["23.0", "170"],  # Heating Set Point = 17.0°C
        ["25.0", "15"],  # Heating Prop. Band = 1.5°C
        ["999.0", "123"],  # Unknown OID (filtered out)
    ]

    return carel_sensors_parse(string_table)


def test_carel_sensors_discovery() -> None:
    """Test discovery of carel_sensors items."""
    discovery_result = list(discover_carel_sensors_temp(parsed()))

    expected = [
        ("Room", {"levels": (30, 35)}),
        ("Delivery", {"levels": (60, 70)}),
        ("Cooling Set Point", {"levels": (60, 70)}),
        ("Cooling Prop. Band", {"levels": (60, 70)}),
        ("Heating Set Point", {"levels": (60, 70)}),
        ("Heating Prop. Band", {"levels": (60, 70)}),
    ]

    # Sort for comparison since order may vary
    assert sorted(discovery_result) == sorted(expected)


def test_carel_sensors_check_room_ok() -> None:
    """Test check function for room sensor with OK status."""
    params = {"levels": (30, 35)}

    result = check_carel_sensors_temp("Room", params, parsed())

    assert result == (0, "26.4 °C", [("temp", 26.4, 30, 35)])


def test_carel_sensors_check_missing_item() -> None:
    """Test check function for missing sensor item."""
    params = {"levels": (30, 35)}

    result = check_carel_sensors_temp("Nonexistent", params, parsed())

    assert result is None


def test_carel_sensors_check_warning_level() -> None:
    """Test check function when temperature exceeds warning level."""
    params = {"levels": (25, 30)}

    result = check_carel_sensors_temp("Room", params, parsed())

    assert result is not None
    state, summary, metrics = result
    assert state == 1  # WARNING
    assert "26.4" in summary
    assert "warn" in summary.lower() or "!" in summary
    assert metrics == [("temp", 26.4, 25, 30)]


def test_carel_sensors_check_critical_level() -> None:
    """Test check function when temperature exceeds critical level."""
    params = {"levels": (20, 22)}

    result = check_carel_sensors_temp("Room", params, parsed())

    assert result is not None
    state, summary, metrics = result
    assert state == 2  # CRITICAL
    assert "26.4" in summary
    assert "crit" in summary.lower() or "!!" in summary
    assert metrics == [("temp", 26.4, 20, 22)]
