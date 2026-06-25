#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.


import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.ups.agent_based.ups_eaton_enviroment import (
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
    assert list(discover_ups_eaton_enviroment(parsed)) == [Service()]


def test_check_ups_eaton_enviroment_with_thresholds(parsed: list[list[str]]) -> None:
    """Test environment check with warning/critical thresholds"""
    params = {
        "temp": (40, 50),
        "remote_temp": (40, 50),
        "humidity": (65, 80),
    }

    result = list(check_ups_eaton_enviroment(params, parsed))

    # temp=1 within thresholds (OK), remote_temp=40 hits warn (WARN), humidity=3 OK
    assert result[0] == Result(state=State.OK, summary="Temperature: 1.0 °C")
    assert result[1] == Metric("temp", 1.0, levels=(40.0, 50.0))
    assert result[2] == Result(
        state=State.WARN,
        summary="Remote-Temperature: 40.0 °C (warn/crit at 40.0 °C/50.0 °C)",
    )
    assert result[4] == Result(state=State.OK, summary="Humidity: 3.0%")
    assert result[5] == Metric("humidity", 3.0, levels=(65.0, 80.0))


def test_check_ups_eaton_enviroment_critical_state(parsed: list[list[str]]) -> None:
    """Test environment check with critical threshold breach"""
    params = {
        "temp": (0, 1),  # temp=1 hits critical
        "remote_temp": (30, 35),  # remote_temp=40 hits critical
        "humidity": (1, 2),  # humidity=3 hits critical
    }

    result = [r for r in check_ups_eaton_enviroment(params, parsed) if isinstance(r, Result)]

    assert result[0].state == State.CRIT
    assert "warn/crit at 0.0 °C/1.0 °C" in result[0].summary
    assert result[1].state == State.CRIT
    assert "warn/crit at 30.0 °C/35.0 °C" in result[1].summary
    assert result[2].state == State.CRIT
    assert "warn/crit at 1.0%/2.0%" in result[2].summary


def test_check_ups_eaton_enviroment_ok_state() -> None:
    """Test environment check with all values OK"""
    good_data = [["25", "30", "50"]]  # temp=25°C, remote_temp=30°C, humidity=50%
    params = {
        "temp": (40, 50),
        "remote_temp": (40, 50),
        "humidity": (65, 80),
    }

    assert list(check_ups_eaton_enviroment(params, good_data)) == [
        Result(state=State.OK, summary="Temperature: 25.0 °C"),
        Metric("temp", 25.0, levels=(40.0, 50.0)),
        Result(state=State.OK, summary="Remote-Temperature: 30.0 °C"),
        Metric("remote_temp", 30.0, levels=(40.0, 50.0)),
        Result(state=State.OK, summary="Humidity: 50.0%"),
        Metric("humidity", 50.0, levels=(65.0, 80.0)),
    ]


def test_parse_ups_eaton_enviroment(string_table: list[list[str]]) -> None:
    """Test that parsing returns the data unchanged"""
    assert parse_ups_eaton_enviroment(string_table) == string_table
