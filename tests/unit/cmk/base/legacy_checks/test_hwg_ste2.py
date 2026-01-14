#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="type-arg"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from cmk.base.check_legacy_includes.hwg import parse_hwg
from cmk.base.legacy_checks.hwg_humidity import (
    check_hwg_humidity,
    discover_hwg_humidity,
)
from cmk.base.legacy_checks.hwg_temp import (
    check_hwg_temp,
    discover_hwg_temp,
)


def test_hwg_ste2_parse() -> None:
    """Test parsing of SNMP data for hwg_ste2."""
    string_table = [
        ["1", "Sensor 215", "1", "23.8", "1"],  # index, descr, status, value, unit (1=°C)
        ["2", "Sensor 216", "1", "34.6", "4"],  # index, descr, status, value, unit (4=%)
    ]

    result = parse_hwg(string_table)

    expected = {
        "1": {
            "descr": "Sensor 215",
            "dev_unit": "c",
            "temperature": 23.8,
            "dev_status_name": "normal",
            "dev_status": "1",
        },
        "2": {
            "descr": "Sensor 216",
            "humidity": 34.6,
            "dev_status_name": "normal",
            "dev_status": "1",
        },
    }

    assert result == expected


def test_hwg_ste2_temperature_discovery() -> None:
    """Test discovery of temperature sensors."""
    parsed = {
        "1": {
            "descr": "Sensor 215",
            "dev_unit": "c",
            "temperature": 23.8,
            "dev_status_name": "normal",
            "dev_status": "1",
        },
        "2": {
            "descr": "Sensor 216",
            "humidity": 34.6,
            "dev_status_name": "normal",
            "dev_status": "1",
        },
    }

    discovery_result = list(discover_hwg_temp(parsed))

    expected: list[tuple[str, dict]] = [("1", {})]

    assert discovery_result == expected


def test_hwg_ste2_humidity_discovery() -> None:
    """Test discovery of humidity sensors."""
    parsed = {
        "1": {
            "descr": "Sensor 215",
            "dev_unit": "c",
            "temperature": 23.8,
            "dev_status_name": "normal",
            "dev_status": "1",
        },
        "2": {
            "descr": "Sensor 216",
            "humidity": 34.6,
            "dev_status_name": "normal",
            "dev_status": "1",
        },
    }

    discovery_result = list(discover_hwg_humidity(parsed))

    expected: list[tuple[str, dict]] = [("2", {})]

    assert discovery_result == expected


def test_hwg_ste2_temperature_check() -> None:
    """Test temperature check function."""
    parsed = {
        "1": {
            "descr": "Sensor 215",
            "dev_unit": "c",
            "temperature": 23.8,
            "dev_status_name": "normal",
            "dev_status": "1",
        },
    }
    params = {"levels": (30, 35)}

    result = list(check_hwg_temp("1", params, parsed))

    assert len(result) == 1
    state, summary, metrics = result[0]
    assert state == 0  # OK
    assert "23.8" in summary
    assert "°C" in summary
    assert "Description: Sensor 215" in summary
    assert "Status: normal" in summary
    assert metrics == [("temp", 23.8, 30.0, 35.0)]


def test_hwg_ste2_humidity_check() -> None:
    """Test humidity check function."""
    parsed = {
        "2": {
            "descr": "Sensor 216",
            "humidity": 34.6,
            "dev_status_name": "normal",
            "dev_status": "1",
        },
    }
    params = {"levels": (60, 70)}

    result1, result2 = list(check_hwg_humidity("2", params, parsed))

    state, summary, metrics = result1
    assert state == 0  # OK
    assert "34.60%" in summary
    assert metrics == [("humidity", 34.6, 60.0, 70.0, 0.0, 100.0)]

    state, summary = result2
    assert "Description: Sensor 216" in summary
    assert "Status: normal" in summary


def test_hwg_ste2_temperature_missing_item() -> None:
    """Test temperature check with missing item."""
    parsed = {"1": {"temperature": 23.8}}
    params = {"levels": (30, 35)}

    result = list(check_hwg_temp("999", params, parsed))

    assert not result


def test_hwg_ste2_humidity_missing_item() -> None:
    """Test humidity check with missing item."""
    parsed = {"2": {"humidity": 34.6}}
    params = {"levels": (60, 70)}

    result = list(check_hwg_humidity("999", params, parsed))

    assert result == []
