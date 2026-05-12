#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# Author: Lars Michelsen <lm@mathias-kettner.de>

# Relevant SNMP OIDs:
# .1.3.6.1.4.1.11.2.14.11.1.2.6.1.1.1 1
# .1.3.6.1.4.1.11.2.14.11.1.2.6.1.2.1 SNMPv2-SMI::enterprises.11.2.3.7.8.3.2
# .1.3.6.1.4.1.11.2.14.11.1.2.6.1.4.1 4
# .1.3.6.1.4.1.11.2.14.11.1.2.6.1.7.1 "Fan Sensor"

# Status codes:
# 1 => unknown,
# 2 => bad,
# 3 => warning
# 4 => good,
# 5 => notPresent

from cmk.agent_based.v2 import (
    any_of,
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)

_STATUS_MAP: dict[str, tuple[State, str]] = {
    "1": (State.UNKNOWN, "unknown"),
    "2": (State.CRIT, "bad"),
    "3": (State.WARN, "warning"),
    "4": (State.OK, "good"),
    "5": (State.WARN, "notPresent"),
}

_SENSOR_TYPE_SUFFIX_MAP = {
    "11.2.3.7.8.3.1": "PSU",
    "11.2.3.7.8.3.2": "FAN",
    "11.2.3.7.8.3.3": "Temp",
    "11.2.3.7.8.3.4": "FutureSlot",
}


def _sensor_type(type_input: str) -> str:
    for suffix, name in _SENSOR_TYPE_SUFFIX_MAP.items():
        if type_input.endswith(suffix):
            return name
    return ""


def parse_hp_procurve_sensors(string_table: StringTable) -> StringTable:
    return string_table


def discover_hp_procurve_sensors(section: StringTable) -> DiscoveryResult:
    for line in section:
        if len(line) == 4 and _STATUS_MAP[line[2]][1] != "notPresent":
            yield Service(item=line[0])


def check_hp_procurve_sensors(item: str, section: StringTable) -> CheckResult:
    for line in section:
        if line[0] == item:
            state, status_readable = _STATUS_MAP[line[2]]
            yield Result(
                state=state,
                summary=f'Condition of {_sensor_type(line[1])} "{line[3]}" is {status_readable}',
            )
            return
    yield Result(state=State.UNKNOWN, summary="item not found in snmp data")


snmp_section_hp_procurve_sensors = SimpleSNMPSection(
    name="hp_procurve_sensors",
    detect=any_of(
        contains(".1.3.6.1.2.1.1.2.0", ".11.2.3.7.11"),
        contains(".1.3.6.1.2.1.1.2.0", ".11.2.3.7.8"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11.2.14.11.1.2.6.1",
        oids=["1", "2", "4", "7"],
    ),
    parse_function=parse_hp_procurve_sensors,
)


check_plugin_hp_procurve_sensors = CheckPlugin(
    name="hp_procurve_sensors",
    service_name="Sensor %s",
    discovery_function=discover_hp_procurve_sensors,
    check_function=check_hp_procurve_sensors,
)
