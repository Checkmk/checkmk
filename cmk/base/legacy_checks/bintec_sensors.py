#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, startswith, StringTable
from cmk.base.check_legacy_includes.fan import check_fan
from cmk.base.check_legacy_includes.temperature import check_temperature

check_info = {}


def parse_bintec_sensors(string_table: StringTable) -> StringTable:
    return string_table


check_info["bintec_sensors"] = LegacyCheckDefinition(
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


def discover_bintec_sensors_fan(info):
    inventory = []
    for _sensor_id, sensor_descr, sensor_type, _sensor_value, _sensor_unit in info:
        if sensor_type == "2":
            inventory.append((sensor_descr, {}))
    return inventory


def check_bintec_sensors_fan(item, params, info):
    for _sensor_id, sensor_descr, _sensor_type, sensor_value, _sensor_unit in info:
        if sensor_descr == item:
            return check_fan(int(sensor_value), params)
    return None


check_info["bintec_sensors.fan"] = LegacyCheckDefinition(
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


def discover_bintec_sensors_temp(info):
    for _sensor_id, sensor_descr, sensor_type, _sensor_value, _sensor_unit in info:
        if sensor_type == "1":
            yield sensor_descr, {}


def check_bintec_sensors_temp(item, params, info):
    for _sensor_id, sensor_descr, _sensor_type, sensor_value, _sensor_unit in info:
        if sensor_descr == item:
            return check_temperature(int(sensor_value), params, "bintec_sensors_%s" % item)

    return 3, "Sensor not found in SNMP data"


check_info["bintec_sensors.temp"] = LegacyCheckDefinition(
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


def discover_bintec_sensors_voltage(info):
    inventory = []
    for _sensor_id, sensor_descr, sensor_type, _sensor_value, _sensor_unit in info:
        if sensor_type == "3":
            inventory.append((sensor_descr, None))
    return inventory


def check_bintec_sensors_voltage(item, _no_params, info):
    for _sensor_id, sensor_descr, _sensor_type, sensor_value, _sensor_unit in info:
        if sensor_descr == item:
            sensor_value = int(sensor_value) / 1000.0

            message = f"{sensor_descr} is at {sensor_value} V"
            perfdata = [("voltage", str(sensor_value) + "V")]

            return 0, message, perfdata

    return 3, "Sensor %s not found" % item


check_info["bintec_sensors.voltage"] = LegacyCheckDefinition(
    name="bintec_sensors_voltage",
    service_name="Voltage %s",
    sections=["bintec_sensors"],
    discovery_function=discover_bintec_sensors_voltage,
    check_function=check_bintec_sensors_voltage,
)

# .
