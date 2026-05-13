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


def parse_arris_cmts_temp(string_table: StringTable) -> StringTable:
    return string_table


def discover_arris_cmts_temp(section: StringTable) -> DiscoveryResult:
    for name, temp in section:
        # only devices with not default temperature
        if temp != "999":
            yield Service(item=name)


def check_arris_cmts_temp(item: str, params: TempParamType, section: StringTable) -> CheckResult:
    for name, temp in section:
        if name == item:
            yield from check_temperature(
                int(temp),
                params,
                unique_name=f"arris_cmts_temp_{item}",
                value_store=get_value_store(),
            )
            return
    yield Result(state=State.UNKNOWN, summary="Sensor not found in SNMP data")


snmp_section_arris_cmts_temp = SimpleSNMPSection(
    name="arris_cmts_temp",
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.4998.2.1"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.4998.1.1.10.1.4.2.1",
        oids=["3", "29"],
    ),
    parse_function=parse_arris_cmts_temp,
)


check_plugin_arris_cmts_temp = CheckPlugin(
    name="arris_cmts_temp",
    service_name="Temperature Module %s",
    discovery_function=discover_arris_cmts_temp,
    check_function=check_arris_cmts_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (40.0, 46.0)},
)
