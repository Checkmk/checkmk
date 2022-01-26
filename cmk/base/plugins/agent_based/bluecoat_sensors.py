#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from typing import Mapping

from .agent_based_api.v1 import contains, register, SNMPTree
from .agent_based_api.v1.type_defs import StringTable

# OID branch 3 means the sensor unit type (from SENSOR-MIB):
# other(1)
# truthvalue(2)
# specialEnum(3)
# volts(4)
# celsius(5)
# rpm(6)


@dataclasses.dataclass(frozen=True)
class Sensor:
    value: float
    is_ok: bool


@dataclasses.dataclass(frozen=True)
class VoltageSensor(Sensor):
    ...


@dataclasses.dataclass(frozen=True)
class Section:
    temperature_sensors: Mapping[str, Sensor]
    other_sensors: Mapping[str, Sensor]


def parse_bluecoat_sensors(string_table: StringTable) -> Section:
    temperature_sensors = {}
    other_sensors = {}

    for name, reading, status, scale, unit in string_table:
        sensor_name = name.replace(" temperature", "")
        value = float(reading) * 10 ** float(scale)
        is_ok = status == "1"

        if unit == "5":
            temperature_sensors[sensor_name] = Sensor(
                value=value,
                is_ok=is_ok,
            )
        else:
            other_sensors[sensor_name] = (VoltageSensor if unit == "4" else Sensor)(
                value=value,
                is_ok=is_ok,
            )

    return Section(
        temperature_sensors=temperature_sensors,
        other_sensors=other_sensors,
    )


register.snmp_section(
    name="bluecoat_sensors",
    parse_function=parse_bluecoat_sensors,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3417.2.1.1.1.1.1",
        oids=[
            "9",
            "5",
            "7",
            "4",
            "3",
        ],
    ),
    detect=contains(
        ".1.3.6.1.2.1.1.2.0",
        "1.3.6.1.4.1.3417.1.1",
    ),
)
