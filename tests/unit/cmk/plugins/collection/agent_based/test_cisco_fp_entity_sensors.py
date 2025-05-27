#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import State
from cmk.plugins.collection.agent_based.cisco_fp_entity_sensors import (
    parse_cisco_fp_entity_sensors,
)
from cmk.plugins.lib.entity_sensors import EntitySensor


def test_parse_cisco_fp_entity_sensors() -> None:
    assert parse_cisco_fp_entity_sensors(
        [
            [],
            [
                ["48", "10", "9", "0", "11040", "1", "1444612113"],
                ["52", "12", "9", "0", "1", "1", "1444612114"],
                ["58", "3", "9", "0", "229", "1", "1444612114"],
                ["59", "5", "9", "0", "0", "1", "1444612114"],
                ["60", "6", "9", "0", "68", "1", "1444612114"],
            ],
        ]
    ) == {
        "current": {
            "Sensor 59": EntitySensor(
                name="Sensor 59", reading=0.0, unit="A", state=State.OK, status_descr="OK"
            ),
        },
        "fan": {
            "Sensor 48": EntitySensor(
                name="Sensor 48", reading=11040.0, unit="RPM", state=State.OK, status_descr="OK"
            ),
        },
        "power": {
            "Sensor 60": EntitySensor(
                name="Sensor 60", reading=68.0, unit="W", state=State.OK, status_descr="OK"
            ),
        },
        "power_presence": {
            "Sensor 52": EntitySensor(
                name="Sensor 52", reading=1.0, unit="boolean", state=State.OK, status_descr="OK"
            ),
        },
        "voltage": {
            "Sensor 58": EntitySensor(
                name="Sensor 58", reading=229.0, unit="V", state=State.OK, status_descr="OK"
            ),
        },
    }
