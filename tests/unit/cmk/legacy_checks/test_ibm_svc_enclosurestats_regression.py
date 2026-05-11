#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Mapping
from typing import Any

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.legacy_checks.ibm_svc_enclosurestats import (
    _check_ibm_svc_enclosurestats_temp,
    check_ibm_svc_enclosurestats_power,
    discover_ibm_svc_enclosurestats_power,
    discover_ibm_svc_enclosurestats_temp,
    parse_ibm_svc_enclosurestats,
)
from cmk.plugins.lib.temperature import TempParamDict

_TEMP_CONFIG_NOTICE = Result(
    state=State.OK,
    notice="Configuration: prefer user levels over device levels (used user levels)",
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

    assert parsed["1"]["power_w"] == 207
    assert parsed["1"]["temp_c"] == 22
    assert parsed["1"]["temp_f"] == 71

    assert parsed["2"]["power_w"] == 126
    assert parsed["2"]["temp_c"] == 21
    assert parsed["2"]["temp_f"] == 69

    assert parsed["3"]["power_w"] == 123
    assert parsed["3"]["temp_c"] == 22
    assert parsed["3"]["temp_f"] == 71

    assert parsed["4"]["power_w"] == 133
    assert parsed["4"]["temp_c"] == 22
    assert parsed["4"]["temp_f"] == 71


def test_discover_ibm_svc_enclosurestats_power(parsed: Mapping[str, Any]) -> None:
    """Test discovery of power monitoring services."""
    result = list(discover_ibm_svc_enclosurestats_power(parsed))
    assert len(result) == 4
    assert Service(item="1") in result
    assert Service(item="2") in result
    assert Service(item="3") in result
    assert Service(item="4") in result


def test_discover_ibm_svc_enclosurestats_temp(parsed: Mapping[str, Any]) -> None:
    """Test discovery of temperature monitoring services."""
    result = list(discover_ibm_svc_enclosurestats_temp(parsed))
    assert len(result) == 4
    assert Service(item="1") in result
    assert Service(item="2") in result
    assert Service(item="3") in result
    assert Service(item="4") in result


def test_check_ibm_svc_enclosurestats_power_basic(parsed: Mapping[str, Any]) -> None:
    """Test basic power monitoring check."""
    result = list(check_ibm_svc_enclosurestats_power("1", parsed))
    assert result == [
        Result(state=State.OK, summary="207 Watt"),
        Metric("power", 207),
    ]


def test_check_ibm_svc_enclosurestats_power_all_enclosures(parsed: Mapping[str, Any]) -> None:
    """Test power monitoring for all enclosures."""
    assert list(check_ibm_svc_enclosurestats_power("1", parsed)) == [
        Result(state=State.OK, summary="207 Watt"),
        Metric("power", 207),
    ]
    assert list(check_ibm_svc_enclosurestats_power("2", parsed)) == [
        Result(state=State.OK, summary="126 Watt"),
        Metric("power", 126),
    ]
    assert list(check_ibm_svc_enclosurestats_power("3", parsed)) == [
        Result(state=State.OK, summary="123 Watt"),
        Metric("power", 123),
    ]
    assert list(check_ibm_svc_enclosurestats_power("4", parsed)) == [
        Result(state=State.OK, summary="133 Watt"),
        Metric("power", 133),
    ]


def test_check_ibm_svc_enclosurestats_temp_default_levels(parsed: Mapping[str, Any]) -> None:
    """Test temperature monitoring with default levels."""
    params: TempParamDict = {"levels": (35.0, 40.0)}
    result = list(_check_ibm_svc_enclosurestats_temp("1", params, parsed, {}))
    assert result == [
        Metric("temp", 22.0, levels=(35.0, 40.0)),
        Result(state=State.OK, summary="Temperature: 22 °C"),
        _TEMP_CONFIG_NOTICE,
    ]


def test_check_ibm_svc_enclosurestats_temp_all_enclosures(parsed: Mapping[str, Any]) -> None:
    """Test temperature monitoring for all enclosures."""
    params: TempParamDict = {"levels": (35.0, 40.0)}

    assert list(_check_ibm_svc_enclosurestats_temp("1", params, parsed, {})) == [
        Metric("temp", 22.0, levels=(35.0, 40.0)),
        Result(state=State.OK, summary="Temperature: 22 °C"),
        _TEMP_CONFIG_NOTICE,
    ]
    assert list(_check_ibm_svc_enclosurestats_temp("2", params, parsed, {})) == [
        Metric("temp", 21.0, levels=(35.0, 40.0)),
        Result(state=State.OK, summary="Temperature: 21 °C"),
        _TEMP_CONFIG_NOTICE,
    ]


def test_check_ibm_svc_enclosurestats_temp_warning_levels() -> None:
    """Test temperature monitoring with warning levels."""
    string_table = [
        ["1", "power_w", "200", "220", "140410113051"],
        ["1", "temp_c", "36", "36", "140410113246"],
        ["1", "temp_f", "97", "97", "140410113246"],
    ]
    parsed = parse_ibm_svc_enclosurestats(string_table)
    params: TempParamDict = {"levels": (35.0, 40.0)}
    result = list(_check_ibm_svc_enclosurestats_temp("1", params, parsed, {}))
    assert result == [
        Metric("temp", 36.0, levels=(35.0, 40.0)),
        Result(state=State.WARN, summary="Temperature: 36 °C (warn/crit at 35.0 °C/40.0 °C)"),
        _TEMP_CONFIG_NOTICE,
    ]


def test_check_ibm_svc_enclosurestats_temp_critical_levels() -> None:
    """Test temperature monitoring with critical levels."""
    string_table = [
        ["1", "power_w", "200", "220", "140410113051"],
        ["1", "temp_c", "41", "41", "140410113246"],
        ["1", "temp_f", "106", "106", "140410113246"],
    ]
    parsed = parse_ibm_svc_enclosurestats(string_table)
    params: TempParamDict = {"levels": (35.0, 40.0)}
    result = list(_check_ibm_svc_enclosurestats_temp("1", params, parsed, {}))
    assert result == [
        Metric("temp", 41.0, levels=(35.0, 40.0)),
        Result(state=State.CRIT, summary="Temperature: 41 °C (warn/crit at 35.0 °C/40.0 °C)"),
        _TEMP_CONFIG_NOTICE,
    ]


def test_check_ibm_svc_enclosurestats_missing_item(parsed: Mapping[str, Any]) -> None:
    """Test checks with missing enclosure items."""
    missing_params: TempParamDict = {"levels": (35.0, 40.0)}
    assert list(check_ibm_svc_enclosurestats_power("999", parsed)) == []
    assert list(_check_ibm_svc_enclosurestats_temp("999", missing_params, parsed, {})) == []


def test_parse_ibm_svc_enclosurestats_invalid_data() -> None:
    """Test parsing with invalid data."""
    string_table = [
        ["1", "power_w", "invalid", "218", "140410113051"],
        ["1", "temp_c", "22", "22", "140410113246"],
        ["2", "power_w", "126", "128", "140410113056"],
    ]
    parsed = parse_ibm_svc_enclosurestats(string_table)
    assert "power_w" not in parsed.get("1", {})
    assert parsed["1"]["temp_c"] == 22
    assert parsed["2"]["power_w"] == 126


def test_discover_ibm_svc_enclosurestats_missing_stats() -> None:
    """Test discovery with missing power or temperature stats."""
    string_table_power_only = [
        ["1", "power_w", "207", "218", "140410113051"],
        ["2", "power_w", "126", "128", "140410113056"],
    ]
    parsed_power_only = parse_ibm_svc_enclosurestats(string_table_power_only)
    assert list(discover_ibm_svc_enclosurestats_power(parsed_power_only)) == [
        Service(item="1"),
        Service(item="2"),
    ]
    assert list(discover_ibm_svc_enclosurestats_temp(parsed_power_only)) == []

    string_table_temp_only = [
        ["1", "temp_c", "22", "22", "140410113246"],
        ["2", "temp_c", "21", "21", "140410113246"],
    ]
    parsed_temp_only = parse_ibm_svc_enclosurestats(string_table_temp_only)
    assert list(discover_ibm_svc_enclosurestats_power(parsed_temp_only)) == []
    assert list(discover_ibm_svc_enclosurestats_temp(parsed_temp_only)) == [
        Service(item="1"),
        Service(item="2"),
    ]


def test_parse_ibm_svc_enclosurestats_empty_data() -> None:
    """Test parsing with empty data."""
    assert parse_ibm_svc_enclosurestats([]) == {}


def test_discover_ibm_svc_enclosurestats_empty_section() -> None:
    """Test discovery with empty section."""
    assert list(discover_ibm_svc_enclosurestats_power({})) == []
    assert list(discover_ibm_svc_enclosurestats_temp({})) == []
