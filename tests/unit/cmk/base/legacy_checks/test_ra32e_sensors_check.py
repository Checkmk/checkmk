#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="type-arg"

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import StringTable
from cmk.base.legacy_checks.ra32e_sensors import (
    check_ra32e_humidity_sensors,
    check_ra32e_power_sensors,
    check_ra32e_sensors,
    check_ra32e_sensors_voltage,
    discover_ra32e_sensors,
    discover_ra32e_sensors_humidity,
    discover_ra32e_sensors_power,
    discover_ra32e_sensors_voltage,
    parse_ra32e_sensors,
)

DISCOVERY_FUNCTIONS = {
    "ra32e_sensors": discover_ra32e_sensors,
    "ra32e_sensors_humidity": discover_ra32e_sensors_humidity,
    "ra32e_sensors_voltage": discover_ra32e_sensors_voltage,
    "ra32e_sensors_power": discover_ra32e_sensors_power,
}

CHECK_FUNCTIONS = {
    "ra32e_sensors": check_ra32e_sensors,
    "ra32e_sensors_humidity": check_ra32e_humidity_sensors,
    "ra32e_sensors_voltage": check_ra32e_sensors_voltage,
    "ra32e_sensors_power": check_ra32e_power_sensors,
}


@pytest.mark.parametrize(
    "info,discoveries_expected,checks_expected",
    [
        (  # internal temperature
            [[["2070", "", ""]], []],
            [
                ("ra32e_sensors", [("Internal", {})]),
                ("ra32e_sensors_humidity", []),
            ],
            [
                (
                    "ra32e_sensors",
                    "Internal",
                    {},
                    (0, "20.7 °C", [("temp", 20.70, None, None)]),
                ),
                ("ra32e_sensors", "Heat Index", {}, (3, "no data for sensor")),
                (
                    "ra32e_sensors_humidity",
                    "Internal",
                    {},
                    (3, "no data for sensor"),
                ),
            ],
        ),
        (  # internal humidity and heat index
            [[["", "6000", "2070"]], []],
            [
                ("ra32e_sensors", [("Heat Index", {})]),
                ("ra32e_sensors_humidity", [("Internal", {})]),
            ],
            [
                ("ra32e_sensors", "Internal", {}, (3, "no data for sensor")),
                (
                    "ra32e_sensors",
                    "Heat Index",
                    {},
                    (0, "20.7 °C", [("temp", 20.70, None, None)]),
                ),
                (
                    "ra32e_sensors_humidity",
                    "Internal",
                    {},
                    (0, "60.00%", [("humidity", 60.0, None, None, 0, 100)]),
                ),
            ],
        ),
        (  # temp sensor (ignores fahrenheit value)
            [[["", "", ""]], [], [["2580", "9999", "", "", ""]], [], [], [], [], [], []],
            [
                ("ra32e_sensors", [("Sensor 2", {})]),
            ],
            [
                ("ra32e_sensors", "Sensor 2", {}, (0, "25.8 °C", [("temp", 25.8, None, None)])),
            ],
        ),
        (  # temp/active sensor
            [[["", "", ""]], [], [], [], [], [["3100", "9999", "0", "", ""]], [], [], []],
            [
                ("ra32e_sensors", [("Sensor 5", {})]),
                ("ra32e_sensors_power", [("Sensor 5", {})]),
            ],
            [
                (
                    "ra32e_sensors",
                    "Sensor 5",
                    {"levels": (30.0, 35.0)},
                    (1, "31.0 °C (warn/crit at 30.0/35.0 °C)", [("temp", 31.0, 30.0, 35.0)]),
                ),
                (
                    "ra32e_sensors_power",
                    "Sensor 5",
                    {},
                    (2, "Device status: no power detected(2)"),
                ),
                (
                    "ra32e_sensors_power",
                    "Sensor 5",
                    {"map_device_states": [("no power detected", 1)]},
                    (1, "Device status: no power detected(2)"),
                ),
            ],
        ),
        (  # temp/analog and humidity sensor
            [
                [["", "", ""]],
                [
                    ["2790", "9999", "7500", "9999", "2800"],
                ],
                [],
                [],
                [],
                [],
                [],
                [],
                [
                    ["2580", "9999", "200", "9999", ""],
                ],
            ],
            [
                ("ra32e_sensors", [("Heat Index 1", {}), ("Sensor 1", {}), ("Sensor 8", {})]),
                ("ra32e_sensors_voltage", [("Sensor 8", {})]),
                ("ra32e_sensors_humidity", [("Sensor 1", {})]),
            ],
            [
                ("ra32e_sensors", "Sensor 8", {}, (0, "25.8 °C", [("temp", 25.8, None, None)])),
                (
                    "ra32e_sensors",
                    "Heat Index 1",
                    {"levels": (27.0, 28.0)},
                    (2, "28.0 °C (warn/crit at 27.0/28.0 °C)", [("temp", 28.0, 27.0, 28.0)]),
                ),
                (
                    "ra32e_sensors_voltage",
                    "Sensor 8",
                    {"voltage": (210, 180)},
                    (
                        1,
                        "Voltage: 200.0 V (warn/crit below 210.0 V/180.0 V)",
                        [("voltage", 200, None, None)],
                    ),
                ),
                (
                    "ra32e_sensors",
                    "Sensor 1",
                    {"levels_lower": (30.0, 25.0)},
                    (1, "27.9 °C (warn/crit below 30.0/25.0 °C)", [("temp", 27.9, None, None)]),
                ),
                (
                    "ra32e_sensors_humidity",
                    "Sensor 1",
                    {"levels_lower": (85.0, 75.0)},
                    (
                        1,
                        "75.00% (warn/crit below 85.00%/75.00%)",
                        [("humidity", 75.0, None, None, 0, 100)],
                    ),
                ),
            ],
        ),
    ],
)
def test_ra32e_sensors_inputs(
    info: list[StringTable],
    discoveries_expected: Sequence[tuple[str, Sequence[object]]],
    checks_expected: Sequence[tuple[str, str, Mapping[str, object], tuple]],
) -> None:
    parsed = parse_ra32e_sensors(info)

    for check, expected in discoveries_expected:
        assert sorted(DISCOVERY_FUNCTIONS[check](parsed)) == expected

    for check, item, params, expected_result in checks_expected:
        assert CHECK_FUNCTIONS[check](item, params, parsed) == expected_result
