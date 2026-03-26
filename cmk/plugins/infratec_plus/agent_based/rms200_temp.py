#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    equals,
    get_value_store,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamType


def discover_rms200_temp(section: StringTable) -> DiscoveryResult:
    for line in section:
        if line[2] != "-27300":
            yield Service(item=line[0])
        # otherwise no sensor is connected


def check_rms200_temp(item: str, params: TempParamType, section: StringTable) -> CheckResult:
    for line in section:
        if line[0] == item:
            yield from check_temperature(
                float(line[2]) / 100,
                params,
                unique_name=f"rms200_temp_{item}",
                value_store=get_value_store(),
            )
            yield Result(state=State.OK, summary=f"({line[1]})")
            return


def parse_rms200_temp(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_rms200_temp = SimpleSNMPSection(
    name="rms200_temp",
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.1909.13"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1909.13.1.1.1",
        oids=["1", "2", "5"],
    ),
    parse_function=parse_rms200_temp,
)


check_plugin_rms200_temp = CheckPlugin(
    name="rms200_temp",
    service_name="Temperature %s ",
    discovery_function=discover_rms200_temp,
    check_function=check_rms200_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (25.0, 28.0)},
)
