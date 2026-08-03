#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Metric,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)
from cmk.plugins.lib.fan import check_fan
from cmk.plugins.lib.temperature import check_temperature, TempParamType


def parse_bintec_sensors(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_bintec_sensors = SimpleSNMPSection(
    name="bintec_sensors",
    parse_function=parse_bintec_sensors,
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.272.4"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.272.4.17.7.1.1.1",
        oids=["2", "3", "4", "5", "7"],
    ),
)

#   .--fans----------------------------------------------------------------.
#   |                          __                                          |
#   |                         / _| __ _ _ __  ___                          |
#   |                        | |_ / _` | '_ \/ __|                         |
#   |                        |  _| (_| | | | \__ \                         |
#   |                        |_|  \__,_|_| |_|___/                         |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_bintec_sensors_fan(section: StringTable) -> DiscoveryResult:
    for _sensor_id, sensor_descr, sensor_type, _sensor_value, _sensor_unit in section:
        if sensor_type == "2":
            yield Service(item=sensor_descr)


def check_bintec_sensors_fan(
    item: str, params: Mapping[str, Any], section: StringTable
) -> CheckResult:
    for _sensor_id, sensor_descr, _sensor_type, sensor_value, _sensor_unit in section:
        if sensor_descr == item:
            yield from check_fan(int(sensor_value), params)
            return


check_plugin_bintec_sensors_fan = CheckPlugin(
    name="bintec_sensors_fan",
    service_name="%s",
    sections=["bintec_sensors"],
    discovery_function=discover_bintec_sensors_fan,
    check_function=check_bintec_sensors_fan,
    check_ruleset_name="hw_fans",
    check_default_parameters={
        "lower": (2000, 1000),
    },
)

# .
#   .--temp----------------------------------------------------------------.
#   |                       _                                              |
#   |                      | |_ ___ _ __ ___  _ __                         |
#   |                      | __/ _ \ '_ ` _ \| '_ \                        |
#   |                      | ||  __/ | | | | | |_) |                       |
#   |                       \__\___|_| |_| |_| .__/                        |
#   |                                        |_|                           |
#   '----------------------------------------------------------------------'


def discover_bintec_sensors_temp(section: StringTable) -> DiscoveryResult:
    for _sensor_id, sensor_descr, sensor_type, _sensor_value, _sensor_unit in section:
        if sensor_type == "1":
            yield Service(item=sensor_descr)


def check_bintec_sensors_temp(
    item: str, params: TempParamType, section: StringTable
) -> CheckResult:
    for _sensor_id, sensor_descr, _sensor_type, sensor_value, _sensor_unit in section:
        if sensor_descr == item:
            yield from check_temperature(
                reading=int(sensor_value),
                params=params,
                unique_name=f"bintec_sensors_{item}",
                value_store=get_value_store(),
            )
            return

    yield Result(state=State.UNKNOWN, summary="Sensor not found in SNMP data")


check_plugin_bintec_sensors_temp = CheckPlugin(
    name="bintec_sensors_temp",
    service_name="Temperature %s",
    sections=["bintec_sensors"],
    discovery_function=discover_bintec_sensors_temp,
    check_function=check_bintec_sensors_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (35.0, 40.0)},
)

# .
#   .--voltage-------------------------------------------------------------.
#   |                             _ _                                      |
#   |                 __   _____ | | |_ __ _  __ _  ___                    |
#   |                 \ \ / / _ \| | __/ _` |/ _` |/ _ \                   |
#   |                  \ V / (_) | | || (_| | (_| |  __/                   |
#   |                   \_/ \___/|_|\__\__,_|\__, |\___|                   |
#   |                                        |___/                         |
#   '----------------------------------------------------------------------'


def discover_bintec_sensors_voltage(section: StringTable) -> DiscoveryResult:
    for _sensor_id, sensor_descr, sensor_type, _sensor_value, _sensor_unit in section:
        if sensor_type == "3":
            yield Service(item=sensor_descr)


def check_bintec_sensors_voltage(item: str, section: StringTable) -> CheckResult:
    for _sensor_id, sensor_descr, _sensor_type, sensor_value, _sensor_unit in section:
        if sensor_descr == item:
            voltage = int(sensor_value) / 1000.0
            yield Result(state=State.OK, summary=f"{sensor_descr} is at {voltage} V")
            yield Metric("voltage", voltage)
            return

    yield Result(state=State.UNKNOWN, summary=f"Sensor {item} not found")


check_plugin_bintec_sensors_voltage = CheckPlugin(
    name="bintec_sensors_voltage",
    service_name="Voltage %s",
    sections=["bintec_sensors"],
    discovery_function=discover_bintec_sensors_voltage,
    check_function=check_bintec_sensors_voltage,
)

# .
