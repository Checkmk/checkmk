#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.entity_sensors import (
    check_entity_sensors_fan,
    check_entity_sensors_power_presence,
    check_entity_sensors_temp,
    discover_entity_sensors_fan,
    discover_entity_sensors_power_presence,
    discover_entity_sensors_temp,
    parse_entity_sensors,
)
from cmk.base.plugins.agent_based.utils.entity_sensors import EntitySensor

_SECTION_CISCO_ENTITY_SENSORS = {
    "fan": {
        "Sensor 47": EntitySensor(
            name="Sensor 47",
            reading=2820.0,
            unit="RPM",
            state=State.OK,
            status_descr="OK",
        ),
    },
    "power_presence": {
        "Sensor 48": EntitySensor(
            name="Sensor 48",
            reading=1.0,
            unit="boolean",
            state=State.OK,
            status_descr="OK",
        ),
    },
}


@pytest.mark.parametrize(
    "string_table, expected_discovery",
    [
        (
            [
                [
                    ["1", "PA-500"],
                    ["2", "Fan #1 Operational"],
                    ["3", "Fan #2 Operational"],
                    ["4", "Temperature at MP [U6]"],
                    ["5", "Temperature at DP [U7]"],
                ],
                [
                    ["2", "10", "9", "1", "1", "rpm"],
                    ["3", "10", "9", "1", "1", "rpm"],
                    ["4", "8", "9", "37", "1", "celsius"],
                    ["5", "8", "9", "40", "1", "celsius"],
                ],
            ],
            [
                Service(item="Sensor at MP [U6]"),
                Service(item="Sensor at DP [U7]"),
            ],
        ),
    ],
)
def test_discover_entity_sensors_temp(string_table, expected_discovery) -> None:
    assert (
        list(discover_entity_sensors_temp(parse_entity_sensors(string_table))) == expected_discovery
    )


@pytest.mark.parametrize(
    "string_table, expected_discovery",
    [
        (
            [
                [
                    ["1", "PA-500"],
                    ["2", "Fan #1 Operational"],
                    ["3", "Fan #2 Operational"],
                    ["4", "Temperature at MP [U6]"],
                    ["5", "Temperature at DP [U7]"],
                ],
                [
                    ["2", "10", "9", "1", "1", "rpm"],
                    ["3", "10", "9", "1", "1", "rpm"],
                    ["4", "8", "9", "37", "1", "celsius"],
                    ["5", "8", "9", "40", "1", "celsius"],
                ],
            ],
            [
                Service(item="Sensor 1 Operational"),
                Service(item="Sensor 2 Operational"),
            ],
        ),
    ],
)
def test_discover_entity_sensors_fan(string_table, expected_discovery) -> None:
    assert (
        list(discover_entity_sensors_fan(parse_entity_sensors(string_table))) == expected_discovery
    )


@pytest.mark.parametrize(
    "string_table, expected_discovery",
    [
        (
            [
                [
                    ["21", "Power Supply 0 Presence Sensor"],
                ],
                [
                    ["21", "12", "9", "1", "1", "truthvalue"],
                ],
            ],
            [
                Service(item="Sensor Power Supply 0 Presence"),
            ],
        ),
    ],
)
def test_discover_entity_sensors_power_presence(string_table, expected_discovery) -> None:
    assert (
        list(discover_entity_sensors_power_presence(parse_entity_sensors(string_table)))
        == expected_discovery
    )


@pytest.mark.parametrize(
    "item, params, section, expected_result",
    [
        (
            "Sensor at DP [U7]",
            {
                "lower": (35.0, 40.0),
            },
            {
                "fan": {
                    "Sensor 1 Operational": EntitySensor(
                        name="Sensor 1 Operational",
                        unit="RPM",
                        reading=1.0,
                        status_descr="OK",
                        state=State.OK,
                    ),
                    "Sensor 2 Operational": EntitySensor(
                        name="Sensor 2 Operational",
                        unit="RPM",
                        reading=1.0,
                        status_descr="OK",
                        state=State.OK,
                    ),
                },
                "temp": {
                    "Sensor at MP [U6]": EntitySensor(
                        name="Sensor at MP [U6]",
                        unit="c",
                        reading=37.0,
                        status_descr="OK",
                        state=State.OK,
                    ),
                    "Sensor at DP [U7]": EntitySensor(
                        name="Sensor at DP [U7]",
                        unit="c",
                        reading=40.0,
                        status_descr="OK",
                        state=State.OK,
                    ),
                },
            },
            [
                Metric("temp", 40.0),
                Result(state=State.OK, summary="Temperature: 40.0°C"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (no levels found)",
                ),
            ],
        ),
        (
            "Sensor at DP [U7]",
            {},
            {
                "temp": {
                    "Sensor at DP [U7]": EntitySensor(
                        name="Sensor at DP [U7]",
                        unit="f",
                        reading=104.0,
                        status_descr="OK",
                        state=State.OK,
                    ),
                },
            },
            [
                Metric("temp", 40.0),
                Result(state=State.OK, summary="Temperature: 40.0°C"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (no levels found)",
                ),
            ],
        ),
    ],
)
def test_check_entity_sensors_temp(item, params, section, expected_result) -> None:
    assert list(check_entity_sensors_temp(item, params, section)) == expected_result


@pytest.mark.parametrize(
    "item, params, section, expected_result",
    [
        (
            "Sensor 1 Operational",
            {
                "lower": (2000, 1000),
            },
            {
                "fan": {
                    "Sensor 1 Operational": EntitySensor(
                        name="Sensor 1 Operational",
                        unit="RPM",
                        reading=1.0,
                        status_descr="OK",
                        state=State.OK,
                    ),
                    "Sensor 2 Operational": EntitySensor(
                        name="Sensor 2 Operational",
                        unit="RPM",
                        reading=1.0,
                        status_descr="OK",
                        state=State.OK,
                    ),
                },
                "temp": {
                    "Sensor at MP [U6]": EntitySensor(
                        name="Sensor at MP [U6]",
                        unit="c",
                        reading=37.0,
                        status_descr="OK",
                        state=State.OK,
                    ),
                    "Sensor at DP [U7]": EntitySensor(
                        name="Sensor at DP [U7]",
                        unit="c",
                        reading=40.0,
                        status_descr="OK",
                        state=State.OK,
                    ),
                },
            },
            [
                Result(state=State.OK, summary="Operational status: OK"),
                Result(
                    state=State.CRIT, summary="Speed: 1 RPM (warn/crit below 2000 RPM/1000 RPM)"
                ),
            ],
        ),
        pytest.param(
            "Sensor 47",
            {
                "lower": (2000, 1000),
            },
            _SECTION_CISCO_ENTITY_SENSORS,
            [
                Result(state=State.OK, summary="Operational status: OK"),
                Result(state=State.OK, summary="Speed: 2820 RPM"),
            ],
            id="Check: Cisco entity Fan Sensors",
        ),
    ],
)
def test_check_entity_sensors_fan(item, params, section, expected_result) -> None:
    assert list(check_entity_sensors_fan(item, params, section)) == expected_result


@pytest.mark.parametrize(
    "item, params, section, expected_result",
    [
        (
            "Sensor Power Supply 0 Presence",
            {
                "power_off_criticality": 1,
            },
            {
                "power_presence": {
                    "Sensor Power Supply 0 Presence": EntitySensor(
                        name="Sensor Power Supply 0 Presence",
                        reading=1.0,
                        unit="boolean",
                        state=State.OK,
                        status_descr="OK",
                    ),
                },
            },
            [
                Result(state=State.OK, summary="Powered on"),
            ],
        ),
        (
            "Sensor Power Supply 0 Presence",
            {
                "power_off_criticality": 2,
            },
            {
                "power_presence": {
                    "Sensor Power Supply 0 Presence": EntitySensor(
                        name="Sensor Power Supply 0 Presence",
                        reading=0.0,
                        unit="boolean",
                        state=State.OK,
                        status_descr="OK",
                    ),
                },
            },
            [
                Result(state=State.CRIT, summary="Powered off"),
            ],
        ),
        pytest.param(
            "Sensor 48",
            {
                "power_off_criticality": 1,
            },
            _SECTION_CISCO_ENTITY_SENSORS,
            [
                Result(state=State.OK, summary="Powered on"),
            ],
            id="Check: Cisco entity power presence Sensors",
        ),
    ],
)
def test_check_entity_sensors_power_presence(item, params, section, expected_result) -> None:
    assert list(check_entity_sensors_power_presence(item, params, section)) == expected_result
