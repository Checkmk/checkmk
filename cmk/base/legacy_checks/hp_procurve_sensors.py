#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

# Author: Lars Michelsen <lm@mathias-kettner.de>

# Relevant SNMP OIDs:
# .1.3.6.1.4.1.11.2.14.11.1.2.6.1.1.1 1
# .1.3.6.1.4.1.11.2.14.11.1.2.6.1.1.2 2
# .1.3.6.1.4.1.11.2.14.11.1.2.6.1.1.3 3
# .1.3.6.1.4.1.11.2.14.11.1.2.6.1.1.4 4
# .1.3.6.1.4.1.11.2.14.11.1.2.6.1.2.1 SNMPv2-SMI::enterprises.11.2.3.7.8.3.2
# .1.3.6.1.4.1.11.2.14.11.1.2.6.1.2.2 SNMPv2-SMI::enterprises.11.2.3.7.8.3.1
# .1.3.6.1.4.1.11.2.14.11.1.2.6.1.2.3 SNMPv2-SMI::enterprises.11.2.3.7.8.3.1
# .1.3.6.1.4.1.11.2.14.11.1.2.6.1.2.4 SNMPv2-SMI::enterprises.11.2.3.7.8.3.3
# .1.3.6.1.4.1.11.2.14.11.1.2.6.1.3.1 1
# .1.3.6.1.4.1.11.2.14.11.1.2.6.1.3.2 1
# .1.3.6.1.4.1.11.2.14.11.1.2.6.1.3.3 1
# .1.3.6.1.4.1.11.2.14.11.1.2.6.1.3.4 1
# .1.3.6.1.4.1.11.2.14.11.1.2.6.1.4.1 4
# .1.3.6.1.4.1.11.2.14.11.1.2.6.1.4.2 4
# .1.3.6.1.4.1.11.2.14.11.1.2.6.1.4.3 5
# .1.3.6.1.4.1.11.2.14.11.1.2.6.1.4.4 4
# .1.3.6.1.4.1.11.2.14.11.1.2.6.1.5.1 0
# .1.3.6.1.4.1.11.2.14.11.1.2.6.1.5.2 0
# .1.3.6.1.4.1.11.2.14.11.1.2.6.1.5.3 0
# .1.3.6.1.4.1.11.2.14.11.1.2.6.1.5.4 0
# .1.3.6.1.4.1.11.2.14.11.1.2.6.1.6.1 0
# .1.3.6.1.4.1.11.2.14.11.1.2.6.1.6.2 0
# .1.3.6.1.4.1.11.2.14.11.1.2.6.1.6.3 0
# .1.3.6.1.4.1.11.2.14.11.1.2.6.1.6.4 0
# .1.3.6.1.4.1.11.2.14.11.1.2.6.1.7.1 "Fan Sensor"
# .1.3.6.1.4.1.11.2.14.11.1.2.6.1.7.2 "Power Supply Sensor"
# .1.3.6.1.4.1.11.2.14.11.1.2.6.1.7.3 "Redundant Power Supply Sensor"
# .1.3.6.1.4.1.11.2.14.11.1.2.6.1.7.4 "Over-temperature Sensor"

# Status codes:
# 1 => unknown,
# 2 => bad,
# 3 => warning
# 4 => good,
# 5 => notPresent

# GENERAL MAPS:


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import any_of, contains, SNMPTree, StringTable

check_info = {}

hp_procurve_status_map = {
    "1": "unknown",
    "2": "bad",
    "3": "warning",
    "4": "good",
    "5": "notPresent",
}
hp_procurve_status2nagios_map = {"unknown": 3, "bad": 2, "warning": 1, "good": 0, "notPresent": 1}


def get_hp_procurve_sensor_type(type_input: str) -> str:
    type_ = ""
    if type_input.endswith("11.2.3.7.8.3.1"):
        type_ = "PSU"
    elif type_input.endswith("11.2.3.7.8.3.2"):
        type_ = "FAN"
    elif type_input.endswith("11.2.3.7.8.3.3"):
        type_ = "Temp"
    elif type_input.endswith("11.2.3.7.8.3.4"):
        type_ = "FutureSlot"
    return type_


def discover_hp_procurve_sensors(info: StringTable) -> list[tuple[str, None]]:
    inventory: list[tuple[str, None]] = []
    for line in info:
        if len(line) == 4 and hp_procurve_status_map[line[2]] != "notPresent":
            inventory.append((line[0], None))
    return inventory


def check_hp_procurve_sensors(item: str, _not_used: None, info: StringTable) -> tuple[int, str]:
    for line in info:
        if line[0] == item:
            procurve_status = hp_procurve_status_map[line[2]]
            status = hp_procurve_status2nagios_map[procurve_status]

            return (
                status,
                f'Condition of {get_hp_procurve_sensor_type(line[1])} "{line[3]}" is {procurve_status}',
            )
    return (3, "item not found in snmp data")


def parse_hp_procurve_sensors(string_table: StringTable) -> StringTable:
    return string_table


check_info["hp_procurve_sensors"] = LegacyCheckDefinition(
    name="hp_procurve_sensors",
    parse_function=parse_hp_procurve_sensors,
    detect=any_of(
        contains(".1.3.6.1.2.1.1.2.0", ".11.2.3.7.11"),
        contains(".1.3.6.1.2.1.1.2.0", ".11.2.3.7.8"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11.2.14.11.1.2.6.1",
        oids=["1", "2", "4", "7"],
    ),
    service_name="Sensor %s",
    discovery_function=discover_hp_procurve_sensors,
    check_function=check_hp_procurve_sensors,
)
