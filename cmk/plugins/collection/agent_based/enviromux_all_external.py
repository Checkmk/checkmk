#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import (
    all_of,
    CheckPlugin,
    exists,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    StringTable,
)
from cmk.plugins.enviromux.lib import (
    check_enviromux_humidity,
    check_enviromux_temperature,
    check_enviromux_voltage,
    discover_enviromux_humidity,
    discover_enviromux_temperature,
    discover_enviromux_voltage,
    ENVIROMUX_CHECK_DEFAULT_PARAMETERS,
    EnviromuxSection,
    EnviromuxSensor,
    SENSOR_TYPE_NAMES,
)


def _parse_value(token: str) -> float | None:
    try:
        return float(token.split()[0])
    except ValueError:
        return None


def parse_enviromux_all_external(string_table: StringTable) -> EnviromuxSection:
    sensors: dict[str, EnviromuxSensor] = {}

    for idx, type_id, description, value_raw, min_raw, max_raw in string_table:
        value = _parse_value(value_raw)
        min_thr = _parse_value(min_raw)
        max_thr = _parse_value(max_raw)

        if value is None:
            continue

        sensors[f"{description} {idx}"] = EnviromuxSensor(
            type_=SENSOR_TYPE_NAMES.get(type_id, "unknown"),
            value=value,
            min_threshold=min_thr,
            max_threshold=max_thr,
        )

    return sensors


snmp_section_enviromux_all_external = SimpleSNMPSection(
    name="enviromux_all_external",
    parse_function=parse_enviromux_all_external,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3699.1.1.11.1.21.1.1",
        oids=[
            "1",  # allExternalSensorIndex
            "3",  # allExternalSensorType
            "4",  # allExternalSensorDescription
            "8",  # allExternalSensorValue
            "10",  # allExternalSensorMinThreshold
            "11",  # allExternalSensorMaxThreshold
        ],
    ),
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.3699.1.1.11"),
        exists(".1.3.6.1.4.1.3699.1.1.11.1.21.1.*"),
    ),
)

# .
#   .--temperature---------------------------------------------------------.
#   |      _                                      _                        |
#   |     | |_ ___ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |     | __/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |     | ||  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      \__\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


check_plugin_enviromux_all_external = CheckPlugin(
    name="enviromux_all_external",
    service_name="Sensor External %s",
    discovery_function=discover_enviromux_temperature,
    check_function=check_enviromux_temperature,
    check_default_parameters={},
    check_ruleset_name="temperature",
)


# .
#   .--Voltage-------------------------------------------------------------.
#   |                 __     __    _ _                                     |
#   |                 \ \   / /__ | | |_ __ _  __ _  ___                   |
#   |                  \ \ / / _ \| | __/ _` |/ _` |/ _ \                  |
#   |                   \ V / (_) | | || (_| | (_| |  __/                  |
#   |                    \_/ \___/|_|\__\__,_|\__, |\___|                  |
#   |                                         |___/                        |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'
check_plugin_enviromux_all_external_voltage = CheckPlugin(
    name="enviromux_all_external_voltage",
    sections=["enviromux_all_external"],
    service_name="Sensor External %s",
    discovery_function=discover_enviromux_voltage,
    check_function=check_enviromux_voltage,
    check_default_parameters=ENVIROMUX_CHECK_DEFAULT_PARAMETERS,
    check_ruleset_name="voltage",
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
#   |                                                                      |
#   '----------------------------------------------------------------------'

check_plugin_enviromux_all_external_humidity = CheckPlugin(
    name="enviromux_all_external_humidity",
    sections=["enviromux_all_external"],
    service_name="Sensor External %s",
    discovery_function=discover_enviromux_humidity,
    check_function=check_enviromux_humidity,
    check_default_parameters={},
    check_ruleset_name="humidity",
)
