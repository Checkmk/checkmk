#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    any_of,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    equals,
    get_value_store,
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

# Example output from agent:
# [['1', '24', 'SLOT #0: TEMP #1'],
# ['2', '12', 'SLOT #0: TEMP #2'],
# ['3', '12', 'SLOT #0: TEMP #3'],
# ['4', '4687', 'FAN #1'],
# ['5', '4560', 'FAN #2'],
# ['6', '4821', 'FAN #3'],
# ['7', '1', 'Power Supply #1'],
# ['8', '1', 'Power Supply #2']]


def _saveint(i: str) -> int:
    try:
        return int(i)
    except (TypeError, ValueError):
        return 0


def parse_brocade(string_table: StringTable) -> StringTable:
    return string_table


def _brocade_sensor_convert(section: StringTable, what: str) -> list[list[str]]:
    return_list = []
    for presence, state, name in section:
        name = name.lstrip()  # remove leading spaces provided via SNMP
        if name.startswith(what) and presence != "6" and (_saveint(state) > 0 or what == "Power"):
            sensor_id = name.split("#")[-1]
            return_list.append([sensor_id, name, state])
    return return_list


snmp_section_brocade = SimpleSNMPSection(
    name="brocade",
    detect=any_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.1588.2.1.1"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.24.1.1588.2.1.1"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.1588.2.2.1"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.1588.3.3.1"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.1916.2.306"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1588.2.1.1.1.1.22.1",
        oids=["3", "4", "5"],
    ),
    parse_function=parse_brocade,
)


def discover_brocade_fan(section: StringTable) -> DiscoveryResult:
    for sensor in _brocade_sensor_convert(section, "FAN"):
        yield Service(item=sensor[0])


def check_brocade_fan(item: str, params: Mapping[str, Any], section: StringTable) -> CheckResult:
    for snmp_item, _name, value in _brocade_sensor_convert(section, "FAN"):
        if item == snmp_item:
            yield from check_fan(int(value), params)
            return


check_plugin_brocade_fan = CheckPlugin(
    name="brocade_fan",
    service_name="FAN %s",
    sections=["brocade"],
    discovery_function=discover_brocade_fan,
    check_function=check_brocade_fan,
    check_ruleset_name="hw_fans",
    check_default_parameters={"lower": (3000, 2800)},
)


def discover_brocade_power(section: StringTable) -> DiscoveryResult:
    for sensor in _brocade_sensor_convert(section, "Power"):
        yield Service(item=sensor[0])


def check_brocade_power(item: str, section: StringTable) -> CheckResult:
    for snmp_item, name, value in _brocade_sensor_convert(section, "Power"):
        if item == snmp_item:
            if int(value) != 1:
                yield Result(state=State.CRIT, summary=f"Error on supply {name}")
                return
            yield Result(state=State.OK, summary="No problems found")
            return
    yield Result(state=State.UNKNOWN, summary="Supply not found")


check_plugin_brocade_power = CheckPlugin(
    name="brocade_power",
    service_name="Power supply %s",
    sections=["brocade"],
    discovery_function=discover_brocade_power,
    check_function=check_brocade_power,
)


def discover_brocade_temp(section: StringTable) -> DiscoveryResult:
    for sensor in _brocade_sensor_convert(section, "SLOT"):
        yield Service(item=sensor[0])


def check_brocade_temp(item: str, params: TempParamType, section: StringTable) -> CheckResult:
    for snmp_item, _name, value in _brocade_sensor_convert(section, "SLOT"):
        if item == snmp_item:
            yield from check_temperature(
                int(value),
                params,
                unique_name=f"brocade_temp_{item}",
                value_store=get_value_store(),
            )
            return


check_plugin_brocade_temp = CheckPlugin(
    name="brocade_temp",
    service_name="Temperature Ambient %s",
    sections=["brocade"],
    discovery_function=discover_brocade_temp,
    check_function=check_brocade_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (55.0, 60.0)},
)
