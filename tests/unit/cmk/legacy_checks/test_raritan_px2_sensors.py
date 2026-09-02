#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.legacy_checks.raritan_px2_sensors import (
    check_raritan_sensors_humidity,
    discover_raritan_px2_sensors_humidity,
)
from cmk.plugins.raritan.lib import parse_raritan_sensors, RaritanSensor

pytestmark = pytest.mark.checks

_SECTION = {
    "Sensor 1": RaritanSensor(
        availability="2",
        state=(State.CRIT, "unavailable"),
        sensor_type="temp",
        sensor_data=[0.0, 10.0, 15.0, 35.0, 30.0],
        sensor_unit="c",
    ),
    "Sensor 2": RaritanSensor(
        availability="1",
        state=(State.OK, "on"),
        sensor_type="humidity",
        sensor_data=[40.0, 10.0, 15.0, 90.0, 85.0],
        sensor_unit="%",
    ),
    "Sensor 3": RaritanSensor(
        availability="2",
        state=(State.CRIT, "unavailable"),
        sensor_type="temp",
        sensor_data=[0.0, 10.0, 15.0, 35.0, 30.0],
        sensor_unit="c",
    ),
    "Sensor 4": RaritanSensor(
        availability="1",
        state=(State.OK, "on"),
        sensor_type="humidity",
        sensor_data=[7.0, 10.0, 15.0, 90.0, 85.0],
        sensor_unit="%",
    ),
    "Sensor 5": RaritanSensor(
        availability="2",
        state=(State.CRIT, "unavailable"),
        sensor_type="temp",
        sensor_data=[0.0, 10.0, 15.0, 35.0, 30.0],
        sensor_unit="c",
    ),
}


def test_parse_raritan_px2_sensors() -> None:
    assert (
        parse_raritan_sensors(
            [
                ["2", "1", "", "10", "-1", "7", "1", "0", "100", "150", "350", "300"],
                ["1", "2", "", "11", "7", "9", "0", "40", "10", "15", "90", "85"],
                ["2", "3", "", "10", "-1", "7", "1", "0", "100", "150", "350", "300"],
                ["1", "4", "", "11", "7", "9", "0", "7", "10", "15", "90", "85"],
                ["2", "5", "", "10", "-1", "7", "1", "0", "100", "150", "350", "300"],
            ]
        )
        == _SECTION
    )


def test_discover_raritan_px2_sensors_humidity() -> None:
    assert list(discover_raritan_px2_sensors_humidity(_SECTION)) == [
        Service(item="Sensor 2"),
        Service(item="Sensor 4"),
    ]


@pytest.mark.parametrize(
    "item, params, expected_result",
    [
        pytest.param(
            "Sensor 2",
            {},
            [
                Result(state=State.OK, summary="40.00%"),
                Metric("humidity", 40.0, levels=(85.0, 90.0), boundaries=(0.0, 100.0)),
                Result(state=State.OK, summary="Device status: on"),
            ],
            id="sensor levels - state OK",
        ),
        pytest.param(
            "Sensor 4",
            {},
            [
                Result(state=State.CRIT, summary="7.00% (warn/crit below 15.00%/10.00%)"),
                Metric("humidity", 7.0, levels=(85.0, 90.0), boundaries=(0.0, 100.0)),
                Result(state=State.OK, summary="Device status: on"),
            ],
            id="sensor levels - state CRIT",
        ),
        pytest.param(
            "Sensor 2",
            {"levels": (35.0, 45.0)},
            [
                Result(state=State.WARN, summary="40.00% (warn/crit at 35.00%/45.00%)"),
                Metric("humidity", 40.0, levels=(35.0, 45.0), boundaries=(0.0, 100.0)),
                Result(state=State.OK, summary="Device status: on"),
            ],
            id="user levels - state WARN",
        ),
        pytest.param(
            "Sensor 4",
            {"levels_lower": (10.0, 8.0)},
            [
                Result(state=State.CRIT, summary="7.00% (warn/crit below 10.00%/8.00%)"),
                Metric("humidity", 7.0, levels=(85.0, 90.0), boundaries=(0.0, 100.0)),
                Result(state=State.OK, summary="Device status: on"),
            ],
            id="user levels lower - State CRIT",
        ),
    ],
)
def test_check_raritan_px2_sensors_humidity(
    item: str,
    params: Mapping[str, tuple[float, float]],
    expected_result: Sequence[Result | Metric],
) -> None:
    assert (
        list(
            check_raritan_sensors_humidity(
                item,
                params,
                _SECTION,
            )
        )
        == expected_result
    )
