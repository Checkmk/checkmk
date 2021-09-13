#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import Check

from .checktestlib import BasicCheckResult

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "info,discoveries_expected,checks_expected",
    [
        (  # internal temperature
            [[["2070", "", ""]], []],
            [
                ("ra32e_sensors", [("Internal", {})]),
                ("ra32e_sensors.humidity", []),
            ],
            [
                (
                    "ra32e_sensors",
                    "Internal",
                    {},
                    BasicCheckResult(0, "20.7 °C", [("temp", 20.70)]),
                ),
                ("ra32e_sensors", "Heat Index", {}, BasicCheckResult(3, "no data for sensor")),
                (
                    "ra32e_sensors.humidity",
                    "Internal",
                    {},
                    BasicCheckResult(3, "no data for sensor"),
                ),
            ],
        ),
        (  # internal humidity and heat index
            [[["", "6000", "2070"]], []],
            [
                ("ra32e_sensors", [("Heat Index", {})]),
                ("ra32e_sensors.humidity", [("Internal", {})]),
            ],
            [
                ("ra32e_sensors", "Internal", {}, BasicCheckResult(3, "no data for sensor")),
                (
                    "ra32e_sensors",
                    "Heat Index",
                    {},
                    BasicCheckResult(0, "20.7 °C", [("temp", 20.70)]),
                ),
                (
                    "ra32e_sensors.humidity",
                    "Internal",
                    {},
                    BasicCheckResult(0, "60.0%", [("humidity", 60.0, None, None, 0, 100)]),
                ),
            ],
        ),
        (  # temp sensor (ignores fahrenheit value)
            [[["", "", ""]], [["2.0", "2580", "9999", "", "", ""]]],
            [
                ("ra32e_sensors", [("Sensor 2", {})]),
            ],
            [
                ("ra32e_sensors", "Sensor 2", {}, BasicCheckResult(0, "25.8 °C", [("temp", 25.8)])),
            ],
        ),
        (  # temp/active sensor
            [[["", "", ""]], [["5.0", "3100", "9999", "0", "", ""]]],
            [
                ("ra32e_sensors", [("Sensor 5", {})]),
                ("ra32e_sensors.power", [("Sensor 5", {})]),
            ],
            [
                (
                    "ra32e_sensors",
                    "Sensor 5",
                    {"levels": (30.0, 35.0)},
                    BasicCheckResult(
                        1, "31.0 °C (warn/crit at 30.0/35.0 °C)", [("temp", 31.0, 30.0, 35.0)]
                    ),
                ),
                (
                    "ra32e_sensors.power",
                    "Sensor 5",
                    {},
                    BasicCheckResult(2, "Device status: no power detected(2)"),
                ),
                (
                    "ra32e_sensors.power",
                    "Sensor 5",
                    {"map_device_states": [("no power detected", 1)]},
                    BasicCheckResult(1, "Device status: no power detected(2)"),
                ),
            ],
        ),
        (  # temp/analog and humidity sensor
            [
                [["", "", ""]],
                [
                    ["1.0", "2790", "9999", "7500", "9999", "2800"],
                    ["8.0", "2580", "9999", "200", "9999", ""],
                ],
            ],
            [
                ("ra32e_sensors", [("Heat Index 1", {}), ("Sensor 1", {}), ("Sensor 8", {})]),
                ("ra32e_sensors.voltage", [("Sensor 8", {})]),
                ("ra32e_sensors.humidity", [("Sensor 1", {})]),
            ],
            [
                ("ra32e_sensors", "Sensor 8", {}, BasicCheckResult(0, "25.8 °C", [("temp", 25.8)])),
                (
                    "ra32e_sensors",
                    "Heat Index 1",
                    {"levels": (27.0, 28.0)},
                    BasicCheckResult(
                        2, "28.0 °C (warn/crit at 27.0/28.0 °C)", [("temp", 28.0, 27.0, 28.0)]
                    ),
                ),
                (
                    "ra32e_sensors.voltage",
                    "Sensor 8",
                    {"voltage": (210, 180)},
                    BasicCheckResult(
                        1, "Voltage: 200.0 V (warn/crit below 210.0 V/180.0 V)", [("voltage", 200)]
                    ),
                ),
                (
                    "ra32e_sensors",
                    "Sensor 1",
                    {"levels_lower": (30.0, 25.0)},
                    BasicCheckResult(1, "27.9 °C (warn/crit below 30.0/25.0 °C)", [("temp", 27.9)]),
                ),
                (
                    "ra32e_sensors.humidity",
                    "Sensor 1",
                    {"levels_lower": (85.0, 75.0)},
                    BasicCheckResult(
                        1,
                        "75.0% (warn/crit below 85.0%/75.0%)",
                        [("humidity", 75.0, None, None, 0, 100)],
                    ),
                ),
            ],
        ),
    ],
)
def test_ra32e_sensors_inputs(info, discoveries_expected, checks_expected):
    ra32e_sensors_checks = [
        "ra32e_sensors",
        "ra32e_sensors.humidity",
        "ra32e_sensors.voltage",
        "ra32e_sensors.power",
    ]

    checks = {name: Check(name) for name in ra32e_sensors_checks}
    parsed = checks["ra32e_sensors"].run_parse(info)

    for check, expected in discoveries_expected:
        result = checks[check].run_discovery(parsed)
        assert sorted(result) == expected

    for check, item, params, expected in checks_expected:
        output = checks[check].run_check(item, params, parsed)
        result = BasicCheckResult(*output)
        assert result == expected
