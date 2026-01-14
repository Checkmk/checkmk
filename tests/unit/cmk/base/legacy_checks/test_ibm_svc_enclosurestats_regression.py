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

from collections.abc import Mapping
from typing import Any

import pytest

from cmk.base.legacy_checks.ibm_svc_enclosurestats import (
    check_ibm_svc_enclosurestats_power,
    check_ibm_svc_enclosurestats_temp,
    discover_ibm_svc_enclosurestats_power,
    discover_ibm_svc_enclosurestats_temp,
    parse_ibm_svc_enclosurestats,
)


@pytest.fixture(name="parsed")
def _parsed() -> Mapping[str, Any]:
    """
    IBM SVC enclosure stats data with power and temperature metrics.
    Each enclosure provides power consumption (watts) and temperature readings (Celsius/Fahrenheit).
    """
    string_table = [
        ["1", "power_w", "207", "218", "140410113051"],
        ["1", "temp_c", "22", "22", "140410113246"],
        ["1", "temp_f", "71", "71", "140410113246"],
        ["2", "power_w", "126", "128", "140410113056"],
        ["2", "temp_c", "21", "21", "140410113246"],
        ["2", "temp_f", "69", "69", "140410113246"],
        ["3", "power_w", "123", "126", "140410113041"],
        ["3", "temp_c", "22", "22", "140410113246"],
        ["3", "temp_f", "71", "71", "140410113246"],
        ["4", "power_w", "133", "138", "140410112821"],
        ["4", "temp_c", "22", "23", "140410112836"],
        ["4", "temp_f", "71", "73", "140410112836"],
    ]
    return parse_ibm_svc_enclosurestats(string_table)


def test_parse_ibm_svc_enclosurestats(parsed: Mapping[str, Any]) -> None:
    """Test parsing of IBM SVC enclosure stats data."""
    assert len(parsed) == 4

    # Check enclosure 1
    assert parsed["1"]["power_w"] == 207
    assert parsed["1"]["temp_c"] == 22
    assert parsed["1"]["temp_f"] == 71

    # Check enclosure 2
    assert parsed["2"]["power_w"] == 126
    assert parsed["2"]["temp_c"] == 21
    assert parsed["2"]["temp_f"] == 69

    # Check enclosure 3
    assert parsed["3"]["power_w"] == 123
    assert parsed["3"]["temp_c"] == 22
    assert parsed["3"]["temp_f"] == 71

    # Check enclosure 4
    assert parsed["4"]["power_w"] == 133
    assert parsed["4"]["temp_c"] == 22
    assert parsed["4"]["temp_f"] == 71


def test_discover_ibm_svc_enclosurestats_power(parsed: Mapping[str, Any]) -> None:
    """Test discovery of power monitoring services."""
    result = list(discover_ibm_svc_enclosurestats_power(parsed))

    assert len(result) == 4
    assert ("1", {}) in result
    assert ("2", {}) in result
    assert ("3", {}) in result
    assert ("4", {}) in result


def test_discover_ibm_svc_enclosurestats_temp(parsed: Mapping[str, Any]) -> None:
    """Test discovery of temperature monitoring services."""
    result = list(discover_ibm_svc_enclosurestats_temp(parsed))

    assert len(result) == 4
    assert ("1", {}) in result
    assert ("2", {}) in result
    assert ("3", {}) in result
    assert ("4", {}) in result


def test_check_ibm_svc_enclosurestats_power_basic(parsed: Mapping[str, Any]) -> None:
    """Test basic power monitoring check."""
    result = check_ibm_svc_enclosurestats_power("1", {}, parsed)

    assert result[0] == 0  # OK state
    assert "207 Watt" in result[1]
    assert result[2] == [("power", 207)]


def test_check_ibm_svc_enclosurestats_power_all_enclosures(parsed: Mapping[str, Any]) -> None:
    """Test power monitoring for all enclosures."""
    # Enclosure 1
    result = check_ibm_svc_enclosurestats_power("1", {}, parsed)
    assert result[0] == 0
    assert "207 Watt" in result[1]
    assert result[2] == [("power", 207)]

    # Enclosure 2
    result = check_ibm_svc_enclosurestats_power("2", {}, parsed)
    assert result[0] == 0
    assert "126 Watt" in result[1]
    assert result[2] == [("power", 126)]

    # Enclosure 3
    result = check_ibm_svc_enclosurestats_power("3", {}, parsed)
    assert result[0] == 0
    assert "123 Watt" in result[1]
    assert result[2] == [("power", 123)]

    # Enclosure 4
    result = check_ibm_svc_enclosurestats_power("4", {}, parsed)
    assert result[0] == 0
    assert "133 Watt" in result[1]
    assert result[2] == [("power", 133)]


def test_check_ibm_svc_enclosurestats_temp_default_levels(parsed: Mapping[str, Any]) -> None:
    """Test temperature monitoring with default levels."""
    params = {"levels": (35, 40)}
    result = check_ibm_svc_enclosurestats_temp("1", params, parsed)

    assert result[0] == 0  # OK state (22°C < 35°C)
    assert "22" in result[1] and "°C" in result[1]
    assert result[2] == [("temp", 22, 35, 40)]


def test_check_ibm_svc_enclosurestats_temp_all_enclosures(parsed: Mapping[str, Any]) -> None:
    """Test temperature monitoring for all enclosures."""
    params = {"levels": (35, 40)}

    # Enclosure 1
    result = check_ibm_svc_enclosurestats_temp("1", params, parsed)
    assert result[0] == 0
    assert "22" in result[1]
    assert result[2] == [("temp", 22, 35, 40)]

    # Enclosure 2
    result = check_ibm_svc_enclosurestats_temp("2", params, parsed)
    assert result[0] == 0
    assert "21" in result[1]
    assert result[2] == [("temp", 21, 35, 40)]

    # Enclosure 3
    result = check_ibm_svc_enclosurestats_temp("3", params, parsed)
    assert result[0] == 0
    assert "22" in result[1]
    assert result[2] == [("temp", 22, 35, 40)]

    # Enclosure 4
    result = check_ibm_svc_enclosurestats_temp("4", params, parsed)
    assert result[0] == 0
    assert "22" in result[1]
    assert result[2] == [("temp", 22, 35, 40)]


def test_check_ibm_svc_enclosurestats_temp_warning_levels() -> None:
    """Test temperature monitoring with warning levels."""
    # Create scenario with temperature at warning level
    string_table = [
        ["1", "power_w", "200", "220", "140410113051"],
        ["1", "temp_c", "36", "36", "140410113246"],
        ["1", "temp_f", "97", "97", "140410113246"],
    ]
    parsed = parse_ibm_svc_enclosurestats(string_table)
    params = {"levels": (35, 40)}

    result = check_ibm_svc_enclosurestats_temp("1", params, parsed)
    assert result[0] == 1  # WARN state (36°C > 35°C)
    assert "36" in result[1]
    assert result[2] == [("temp", 36, 35, 40)]


def test_check_ibm_svc_enclosurestats_temp_critical_levels() -> None:
    """Test temperature monitoring with critical levels."""
    # Create scenario with temperature at critical level
    string_table = [
        ["1", "power_w", "200", "220", "140410113051"],
        ["1", "temp_c", "41", "41", "140410113246"],
        ["1", "temp_f", "106", "106", "140410113246"],
    ]
    parsed = parse_ibm_svc_enclosurestats(string_table)
    params = {"levels": (35, 40)}

    result = check_ibm_svc_enclosurestats_temp("1", params, parsed)
    assert result[0] == 2  # CRIT state (41°C > 40°C)
    assert "41" in result[1]
    assert result[2] == [("temp", 41, 35, 40)]


def test_check_ibm_svc_enclosurestats_missing_item(parsed: Mapping[str, Any]) -> None:
    """Test checks with missing enclosure items."""
    # Non-existent enclosure
    result = check_ibm_svc_enclosurestats_power("999", {}, parsed)
    assert result is None

    result = check_ibm_svc_enclosurestats_temp("999", {"levels": (35, 40)}, parsed)
    assert result is None


def test_parse_ibm_svc_enclosurestats_invalid_data() -> None:
    """Test parsing with invalid data."""
    string_table = [
        ["1", "power_w", "invalid", "218", "140410113051"],  # Invalid stat_current
        ["1", "temp_c", "22", "22", "140410113246"],
        ["2", "power_w", "126", "128", "140410113056"],
    ]
    parsed = parse_ibm_svc_enclosurestats(string_table)

    # Should skip invalid power data but keep valid temp data
    assert "power_w" not in parsed.get("1", {})
    assert parsed["1"]["temp_c"] == 22
    assert parsed["2"]["power_w"] == 126


def test_discover_ibm_svc_enclosurestats_missing_stats() -> None:
    """Test discovery with missing power or temperature stats."""
    # Only power data, no temperature
    string_table_power_only = [
        ["1", "power_w", "207", "218", "140410113051"],
        ["2", "power_w", "126", "128", "140410113056"],
    ]
    parsed_power_only = parse_ibm_svc_enclosurestats(string_table_power_only)

    power_items = list(discover_ibm_svc_enclosurestats_power(parsed_power_only))
    temp_items = list(discover_ibm_svc_enclosurestats_temp(parsed_power_only))

    assert len(power_items) == 2
    assert len(temp_items) == 0

    # Only temperature data, no power
    string_table_temp_only = [
        ["1", "temp_c", "22", "22", "140410113246"],
        ["2", "temp_c", "21", "21", "140410113246"],
    ]
    parsed_temp_only = parse_ibm_svc_enclosurestats(string_table_temp_only)

    power_items = list(discover_ibm_svc_enclosurestats_power(parsed_temp_only))
    temp_items = list(discover_ibm_svc_enclosurestats_temp(parsed_temp_only))

    assert len(power_items) == 0
    assert len(temp_items) == 2


def test_parse_ibm_svc_enclosurestats_empty_data() -> None:
    """Test parsing with empty data."""
    parsed = parse_ibm_svc_enclosurestats([])
    assert parsed == {}


def test_discover_ibm_svc_enclosurestats_empty_section() -> None:
    """Test discovery with empty section."""
    power_items = list(discover_ibm_svc_enclosurestats_power({}))
    temp_items = list(discover_ibm_svc_enclosurestats_temp({}))

    assert len(power_items) == 0
    assert len(temp_items) == 0
