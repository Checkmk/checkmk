#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    OIDEnd,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.bvip.lib import DETECT_BVIP
from cmk.plugins.lib.temperature import check_temperature, TempParamType


def parse_bvip_temp(string_table: StringTable) -> StringTable:
    return string_table


def discover_bvip_temp(section: StringTable) -> DiscoveryResult:
    for line in section:
        # line[0] contains nice names like "CPU" and "System"
        yield Service(item=line[0])


def check_bvip_temp(item: str, params: TempParamType, section: StringTable) -> CheckResult:
    for nr, value in section:
        if nr == item:
            yield from check_temperature(
                float(value) / 10,
                params,
                unique_name=f"bvip_temp_{item}",
                value_store=get_value_store(),
            )
            return


snmp_section_bvip_temp = SimpleSNMPSection(
    name="bvip_temp",
    detect=DETECT_BVIP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3967.1.1.7.1",
        oids=[OIDEnd(), "1"],
    ),
    parse_function=parse_bvip_temp,
)


check_plugin_bvip_temp = CheckPlugin(
    name="bvip_temp",
    service_name="Temperature %s",
    discovery_function=discover_bvip_temp,
    check_function=check_bvip_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (50.0, 60.0)},
)
