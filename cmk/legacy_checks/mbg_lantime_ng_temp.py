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
from cmk.plugins.lib.temperature import check_temperature, TempParamType
from cmk.plugins.meinberg.liblantime import DETECT_MBG_LANTIME_NG


def discover_mbg_lantime_ng_temp(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service(item="System")


def check_mbg_lantime_ng_temp(
    item: str, params: TempParamType, section: StringTable
) -> CheckResult:
    yield from check_temperature(
        reading=float(section[0][0]),
        params=params,
        unique_name=f"mbg_lantime_ng_temp_{item}",
        value_store=get_value_store(),
    )


def parse_mbg_lantime_ng_temp(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_mbg_lantime_ng_temp = SimpleSNMPSection(
    name="mbg_lantime_ng_temp",
    detect=DETECT_MBG_LANTIME_NG,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.5597.30.0.5.2",
        oids=["1"],
    ),
    parse_function=parse_mbg_lantime_ng_temp,
)


check_plugin_mbg_lantime_ng_temp = CheckPlugin(
    name="mbg_lantime_ng_temp",
    service_name="Temperature %s",
    discovery_function=discover_mbg_lantime_ng_temp,
    check_function=check_mbg_lantime_ng_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (80.0, 90.0),  # levels for system temperature
    },
)
