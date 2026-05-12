#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


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
from cmk.plugins.lib.fan import check_fan
from cmk.plugins.lib.temperature import check_temperature, TempParamType

# example output
# .1.3.6.1.4.1.232.167.2.4.5.2.1.2.1 4
# .1.3.6.1.4.1.232.167.2.4.5.2.1.2.2 8
# .1.3.6.1.4.1.232.167.2.4.5.2.1.2.3 7
# .1.3.6.1.4.1.232.167.2.4.5.2.1.3.1 Temperature In
# .1.3.6.1.4.1.232.167.2.4.5.2.1.3.2 Warning message
# .1.3.6.1.4.1.232.167.2.4.5.2.1.3.3 Alarm message
# .1.3.6.1.4.1.232.167.2.4.5.2.1.4.1 4
# .1.3.6.1.4.1.232.167.2.4.5.2.1.4.2 4
# .1.3.6.1.4.1.232.167.2.4.5.2.1.4.3 4
# .1.3.6.1.4.1.232.167.2.4.5.2.1.5.1 20

Section = Mapping[str, Mapping[str, Any]]

_TEMP_TYPES = frozenset({4, 5, 13, 14, 15, 16, 17, 18, 19, 20})
_FAN_TYPES = frozenset({9, 10, 11, 26, 27, 28})


def parse_hp_mcs_sensors(string_table: StringTable) -> Section:
    return {
        line[0]: {
            "type": int(line[1]),
            "name": line[2],
            "status": int(line[3]),
            "value": float(line[4]),
            "high": float(line[5]),
            "low": float(line[6]),
        }
        for line in string_table
    }


snmp_section_hp_mcs_sensors = SimpleSNMPSection(
    name="hp_mcs_sensors",
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.232.167"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.232.167.2.4.5.2.1",
        oids=["1", "2", "3", "4", "5", "6", "7"],
    ),
    parse_function=parse_hp_mcs_sensors,
)


def discover_hp_mcs_sensors(section: Section) -> DiscoveryResult:
    for entry in section.values():
        if entry["type"] in _TEMP_TYPES:
            yield Service(item=entry["name"])


def check_hp_mcs_sensors(item: str, params: TempParamType, section: Section) -> CheckResult:
    for key, entry in section.items():
        if entry["name"] == item:
            yield from check_temperature(
                entry["value"],
                params,
                unique_name=f"hp_mcs_sensors_{key}",
                value_store=get_value_store(),
            )
            return


check_plugin_hp_mcs_sensors = CheckPlugin(
    name="hp_mcs_sensors",
    service_name="Sensor %s",
    discovery_function=discover_hp_mcs_sensors,
    check_function=check_hp_mcs_sensors,
    check_ruleset_name="temperature",
    check_default_parameters={},
)


def discover_hp_mcs_sensors_fan(section: Section) -> DiscoveryResult:
    for entry in section.values():
        if entry["type"] in _FAN_TYPES:
            yield Service(item=entry["name"])


def check_hp_mcs_sensors_fan(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    for entry in section.values():
        if entry["name"] == item:
            yield from check_fan(entry["value"], params)
            return


check_plugin_hp_mcs_sensors_fan = CheckPlugin(
    name="hp_mcs_sensors_fan",
    service_name="Sensor %s",
    sections=["hp_mcs_sensors"],
    discovery_function=discover_hp_mcs_sensors_fan,
    check_function=check_hp_mcs_sensors_fan,
    check_ruleset_name="hw_fans",
    check_default_parameters={
        "lower": (1000, 500),
    },
)
