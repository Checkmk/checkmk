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
    StringTable,
)
from cmk.plugins.huawei.lib import DETECT_HUAWEI_OSN
from cmk.plugins.lib.temperature import check_temperature, TempParamType

# The laser should not get hotter than 70°C


def discover_huawei_osn_temp(section: StringTable) -> DiscoveryResult:
    for line in section:
        yield Service(item=line[1])


def check_huawei_osn_temp(item: str, params: TempParamType, section: StringTable) -> CheckResult:
    for line in section:
        if item == line[1]:
            temp = float(line[0]) / 10.0
            yield from check_temperature(
                reading=temp,
                params=params,
                unique_name=f"huawei_osn_temp_{item}",
                value_store=get_value_store(),
            )


def parse_huawei_osn_temp(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_huawei_osn_temp = SimpleSNMPSection(
    name="huawei_osn_temp",
    detect=DETECT_HUAWEI_OSN,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2011.2.25.3.40.50.76.10.1",
        oids=["2.190", "6.190"],
    ),
    parse_function=parse_huawei_osn_temp,
)


check_plugin_huawei_osn_temp = CheckPlugin(
    name="huawei_osn_temp",
    service_name="Temperature %s",
    discovery_function=discover_huawei_osn_temp,
    check_function=check_huawei_osn_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (70.0, 80.0),
    },
)
