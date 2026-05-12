#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


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
from cmk.plugins.lib.temperature import check_temperature, TempParamType

# .1.3.6.1.4.1.11.2.14.11.1.2.8.1.1.2.0 Sys-1   # system name
# .1.3.6.1.4.1.11.2.14.11.1.2.8.1.1.3.0 21C     # current temperature
# .1.3.6.1.4.1.11.2.14.11.1.2.8.1.1.4.0 22C     # maximum temperature
# .1.3.6.1.4.1.11.2.14.11.1.2.8.1.1.5.0 18C     # minimum temperature
# .1.3.6.1.4.1.11.2.14.11.1.2.8.1.1.6.0 2       # Over temperature
# .1.3.6.1.4.1.11.2.14.11.1.2.8.1.1.7.0 57C     # temperature threshold
# .1.3.6.1.4.1.11.2.14.11.1.2.8.1.1.9.0 17      # average temperature


def parse_hp_procurve_temp(string_table: StringTable) -> StringTable:
    return string_table


def discover_hp_procurve_temp(section: StringTable) -> DiscoveryResult:
    if len(section) == 1:
        yield Service(item=section[0][0])


def check_hp_procurve_temp(item: str, params: TempParamType, section: StringTable) -> CheckResult:
    if len(section) != 1:
        return
    raw = section[0][1]
    temp, dev_unit = int(raw[:-1]), raw[-1].lower()
    yield from check_temperature(
        temp,
        params,
        unique_name=f"hp_procurve_temp_{item}",
        value_store=get_value_store(),
        dev_unit=dev_unit,
    )


snmp_section_hp_procurve_temp = SimpleSNMPSection(
    name="hp_procurve_temp",
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.11.2.3.7.11"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11.2.14.11.1.2.8.1.1",
        oids=["2", "3"],
    ),
    parse_function=parse_hp_procurve_temp,
)


check_plugin_hp_procurve_temp = CheckPlugin(
    name="hp_procurve_temp",
    service_name="Temperature %s",
    discovery_function=discover_hp_procurve_temp,
    check_function=check_hp_procurve_temp,
    check_ruleset_name="temperature",
    check_default_parameters={},
)
