#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.hwg.agent_based.hwg_sensor import check_hwg_sensor, discover_hwg_sensor
from cmk.plugins.hwg.agent_based.lib import parse_hwg

_STE2_WALK: StringTable = [
    ["1", "Sensor 40437", "1", "22.6", "1"],
    ["2", "Sensor 40937", "1", "43.8", "4"],
    ["3", "TVOC", "1", "107", "0"],
    ["4", "Press", "1", "948.9", "0"],
    ["5", "Sensor 60612", "1", "22.3", "1"],
]


def test_discover_hwg_sensor_finds_only_sensors_without_unit() -> None:
    section = parse_hwg(_STE2_WALK)

    services = list(discover_hwg_sensor(section))

    assert services == [Service(item="3"), Service(item="4")]


def test_discover_hwg_sensor_finds_sensor_with_unknown_unit() -> None:
    section = parse_hwg([["6", "Sensor 6", "1", "5", "9"]])

    services = list(discover_hwg_sensor(section))

    assert services == [Service(item="6")]


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("n/a", id="unreadable value"),
        pytest.param("0", id="zero value"),
    ],
)
def test_discover_hwg_sensor_finds_sensor_with_unreadable_or_zero_value(value: str) -> None:
    section = parse_hwg([["3", "TVOC", "1", value, "0"]])

    services = list(discover_hwg_sensor(section))

    assert services == [Service(item="3")]


@pytest.mark.parametrize(
    "status",
    [
        pytest.param("0", id="invalid"),
        pytest.param("7", id="unknown status code"),
    ],
)
def test_discover_hwg_sensor_skips_sensor_without_valid_status(status: str) -> None:
    section = parse_hwg([["3", "TVOC", status, "107", "0"]])

    assert not list(discover_hwg_sensor(section))


def test_check_hwg_sensor_is_ok_without_levels() -> None:
    section = parse_hwg(_STE2_WALK)

    results = list(check_hwg_sensor("4", {}, section))

    assert results == [
        Result(state=State.OK, summary="Value: 948.90"),
        Metric("generic_number", 948.9),
        Result(state=State.OK, summary="Description: Press"),
        Result(state=State.OK, summary="Status: normal"),
    ]


@pytest.mark.parametrize(
    "status, expected",
    [
        pytest.param("2", Result(state=State.CRIT, summary="Status: out of range low"), id="out of range low"),
        pytest.param("5", Result(state=State.CRIT, summary="Status: alarm high"), id="alarm high"),
        pytest.param("0", Result(state=State.UNKNOWN, summary="Status: invalid"), id="invalid"),
    ],
)  # fmt: skip
def test_check_hwg_sensor_state_follows_device_status(status: str, expected: Result) -> None:
    section = parse_hwg([["3", "TVOC", status, "107", "0"]])

    results = list(check_hwg_sensor("3", {}, section))

    assert results[-1] == expected


def test_check_hwg_sensor_applies_upper_levels() -> None:
    section = parse_hwg(_STE2_WALK)

    results = list(check_hwg_sensor("3", {"levels": (50.0, 100.0)}, section))

    assert results[0] == Result(
        state=State.CRIT, summary="Value: 107.00 (warn/crit at 50.00/100.00)"
    )


def test_check_hwg_sensor_applies_lower_levels() -> None:
    section = parse_hwg(_STE2_WALK)

    results = list(check_hwg_sensor("4", {"levels_lower": (1000.0, 900.0)}, section))

    assert results[0] == Result(
        state=State.WARN, summary="Value: 948.90 (warn/crit below 1000.00/900.00)"
    )


def test_check_hwg_sensor_is_unknown_for_unreadable_value() -> None:
    section = parse_hwg([["3", "TVOC", "1", "n/a", "0"]])

    results = list(check_hwg_sensor("3", {}, section))

    assert results == [
        Result(state=State.UNKNOWN, summary="Value: not readable"),
        Result(state=State.OK, summary="Description: TVOC"),
        Result(state=State.OK, summary="Status: normal"),
    ]


def test_check_hwg_sensor_ignores_temperature_sensor() -> None:
    section = parse_hwg(_STE2_WALK)

    assert not list(check_hwg_sensor("1", {}, section))
