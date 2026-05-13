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
from cmk.plugins.avaya.lib import DETECT_AVAYA
from cmk.plugins.lib.temperature import check_temperature, TempParamType


def parse_avaya_chassis_temp(string_table: StringTable) -> StringTable:
    return string_table


def discover_avaya_chassis_temp(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service(item="Chassis")


def check_avaya_chassis_temp(item: str, params: TempParamType, section: StringTable) -> CheckResult:
    yield from check_temperature(
        int(section[0][0]),
        params,
        unique_name=f"avaya_chassis_temp_{item}",
        value_store=get_value_store(),
    )


snmp_section_avaya_chassis_temp = SimpleSNMPSection(
    name="avaya_chassis_temp",
    detect=DETECT_AVAYA,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2272.1.100.1",
        oids=["2"],
    ),
    parse_function=parse_avaya_chassis_temp,
)


check_plugin_avaya_chassis_temp = CheckPlugin(
    name="avaya_chassis_temp",
    service_name="Temperature %s",
    discovery_function=discover_avaya_chassis_temp,
    check_function=check_avaya_chassis_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (55.0, 60.0),
    },
)
