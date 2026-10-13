#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    all_of,
    any_of,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    exists,
    get_value_store,
    not_exists,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamType

# We fetch the following columns from SNMP:
# 13: name of the temperature sensor (used as item)
# 11: current temperature in C
# 6:  warning level
# 8:  critical level


def discover_fsc_temp(section: StringTable) -> DiscoveryResult:
    # Ignore non-connected sensors
    yield from (Service(item=line[0]) for line in section if int(line[1]) < 500)


def check_fsc_temp(item: str, params: TempParamType, section: StringTable) -> CheckResult:
    for name, rawtemp, warn, crit in section:
        if name == item:
            temp = int(rawtemp)
            if temp in {-1, 4294967295}:
                yield Result(state=State.UNKNOWN, summary="Sensor or component missing")
                return

            yield from check_temperature(
                temp,
                params,
                unique_name=f"fsc_temp_{item}",
                value_store=get_value_store(),
                dev_levels=(int(warn), int(crit)),
            )
            return


def parse_fsc_temp(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_fsc_temp = SimpleSNMPSection(
    name="fsc_temp",
    parse_function=parse_fsc_temp,
    detect=all_of(
        all_of(
            any_of(
                startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.231"),
                startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.311"),
                startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.8072"),
            ),
            exists(".1.3.6.1.4.1.231.2.10.2.1.1.0"),
        ),
        not_exists(".1.3.6.1.4.1.231.2.10.2.2.10.5.1.1.3.*"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.231.2.10.2.2.5.2.1.1",
        oids=["13", "11", "6", "8"],
    ),
)


check_plugin_fsc_temp = CheckPlugin(
    name="fsc_temp",
    service_name="Temperature %s",
    discovery_function=discover_fsc_temp,
    check_function=check_fsc_temp,
    check_ruleset_name="temperature",
    check_default_parameters={},
)
