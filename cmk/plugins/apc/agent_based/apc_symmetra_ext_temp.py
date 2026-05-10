#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.apc.lib_ats import DETECT
from cmk.plugins.lib.temperature import check_temperature, TempParamType


def discover_apc_symmetra_ext_temp(section: StringTable) -> DiscoveryResult:
    for index, status, _temp, _temp_unit in section:
        if status == "2":
            yield Service(item=index)


def check_apc_symmetra_ext_temp(
    item: str, params: TempParamType, section: StringTable
) -> CheckResult:
    for index, _status, temp, temp_unit in section:
        if item == index:
            yield from check_temperature(
                reading=int(temp),
                params=params,
                unique_name=item,
                value_store=get_value_store(),
                dev_unit="f" if temp_unit == "2" else "c",
            )
            return

    yield Result(state=State.UNKNOWN, summary="Sensor not found in SNMP data")


def parse_apc_symmetra_ext_temp(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_apc_symmetra_ext_temp = SimpleSNMPSection(
    name="apc_symmetra_ext_temp",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.318.1.1.10.2.3.2.1",
        oids=["1", "3", "4", "5"],
    ),
    parse_function=parse_apc_symmetra_ext_temp,
)


check_plugin_apc_symmetra_ext_temp = CheckPlugin(
    name="apc_symmetra_ext_temp",
    service_name="Temperature External %s",
    discovery_function=discover_apc_symmetra_ext_temp,
    check_function=check_apc_symmetra_ext_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (30.0, 35.0)},
)
