#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from typing import Mapping

from .agent_based_api.v1 import (
    contains,
    get_value_store,
    Metric,
    register,
    Result,
    Service,
    SNMPTree,
    State,
)
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.temperature import check_temperature, TempParamType

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


def discover_bluecoat_sensors(section: Section) -> DiscoveryResult:
    yield from (Service(item=sensor_name) for sensor_name in section.other_sensors)


def check_bluecoat_sensors(
    item: str,
    section: Section,
) -> CheckResult:
    if not (sensor := section.other_sensors.get(item)):
        return

    state = State.OK if sensor.is_ok else State.CRIT

    if not isinstance(
        sensor,
        VoltageSensor,
    ):
        yield Result(
            state=state,
            summary=f"{sensor.value:.1f}",
        )
        return

    yield Result(
        state=state,
        summary=f"{sensor.value:.1f} V",
    )
    yield Metric(
        name="voltage",
        value=sensor.value,
    )


register.check_plugin(
    name="bluecoat_sensors",
    service_name="%s",
    discovery_function=discover_bluecoat_sensors,
    check_function=check_bluecoat_sensors,
)


def discover_bluecoat_sensors_temp(section: Section) -> DiscoveryResult:
    yield from (Service(item=sensor_name) for sensor_name in section.temperature_sensors)


def check_bluecoat_sensors_temp(
    item: str,
    params: TempParamType,
    section: Section,
) -> CheckResult:
    if not (sensor := section.temperature_sensors.get(item)):
        return
    yield from check_temperature(
        reading=sensor.value,
        params=params,
        unique_name=item,
        value_store=get_value_store(),
        dev_status=0 if sensor.is_ok else 2,
        dev_status_name="OK" if sensor.is_ok else "Not OK",
    )


register.check_plugin(
    name="bluecoat_sensors_temp",
    sections=["bluecoat_sensors"],
    service_name="%s",
    discovery_function=discover_bluecoat_sensors_temp,
    check_function=check_bluecoat_sensors_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"device_levels_handling": "devdefault"},
)
