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
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    StringTable,
)
from cmk.plugins.lib.humidity import check_humidity
from cmk.plugins.lib.temperature import check_temperature, TempParamType

#   .--Temperature---------------------------------------------------------.
#   |     _____                                   _                        |
#   |    |_   _|__ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |      | |/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |      | |  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      |_|\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   +----------------------------------------------------------------------+

# ambient temperature levels for a datacenter


def _sensor_descr(sensor_id: str) -> str:
    if sensor_id == "0":
        return "internal"
    return f"external {sensor_id}"


def parse_bluenet_sensor(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_bluenet_sensor = SimpleSNMPSection(
    name="bluenet_sensor",
    parse_function=parse_bluenet_sensor,
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.21695.1"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.21695.1.10.7.3.1",
        oids=["1", "2", "4", "5"],
    ),
)


def discover_bluenet_sensor_temp(section: StringTable) -> DiscoveryResult:
    for sensor_id, sensor_type, _temp, _hum in section:
        # temperature and combined temperature/humidity sensor
        if sensor_type in ("1", "2"):
            yield Service(item=_sensor_descr(sensor_id))


def check_bluenet_sensor_temp(
    item: str, params: TempParamType, section: StringTable
) -> CheckResult:
    for sensor_id, _sensor_type, temp, _hum in section:
        if _sensor_descr(sensor_id) == item:
            temperature = float(temp) / 10.0
            yield from check_temperature(
                reading=temperature,
                params=params,
                unique_name=f"bluenet_sensor_temp_{item}",
                value_store=get_value_store(),
                dev_unit="c",
            )
            return


check_plugin_bluenet_sensor = CheckPlugin(
    name="bluenet_sensor",
    service_name="Temperature %s",
    discovery_function=discover_bluenet_sensor_temp,
    check_function=check_bluenet_sensor_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (28.0, 35.0),
        "levels_lower": (13.0, 17.0),
    },
)

# .
#   .--Humidity------------------------------------------------------------.
#   |              _   _                 _     _ _ _                       |
#   |             | | | |_   _ _ __ ___ (_) __| (_) |_ _   _               |
#   |             | |_| | | | | '_ ` _ \| |/ _` | | __| | | |              |
#   |             |  _  | |_| | | | | | | | (_| | | |_| |_| |              |
#   |             |_| |_|\__,_|_| |_| |_|_|\__,_|_|\__|\__, |              |
#   |                                                  |___/               |
#   +----------------------------------------------------------------------+

# ambient humidity levels for a datacenter
bluenet_sensor_humidity_default_levels = (35, 40, 60, 65)


def discover_bluenet_sensor_hum(section: StringTable) -> DiscoveryResult:
    for sensor_id, sensor_type, _temp, _hum in section:
        # humidity for combined temperature/humidity sensor
        if sensor_type == "2":
            yield Service(
                item=_sensor_descr(sensor_id),
                parameters={"levels": (60, 65), "levels_lower": (40, 35)},
            )


def check_bluenet_sensor_hum(
    item: str, params: Mapping[str, Any], section: StringTable
) -> CheckResult:
    for sensor_id, _sensor_type, _temp, hum in section:
        if _sensor_descr(sensor_id) == item:
            humidity = float(hum) / 10.0
            yield from check_humidity(humidity, params)
            return


check_plugin_bluenet_sensor_hum = CheckPlugin(
    name="bluenet_sensor_hum",
    service_name="Humidity %s",
    sections=["bluenet_sensor"],
    discovery_function=discover_bluenet_sensor_hum,
    check_function=check_bluenet_sensor_hum,
    check_ruleset_name="humidity",
    check_default_parameters={},
)
