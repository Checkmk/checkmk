#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.meinberg.liblantime import DETECT_MBG_LANTIME_NG

type Section = StringTable


def discover_mbg_lantime_ng_power(section: Section) -> DiscoveryResult:
    for line in section:
        yield Service(item=line[0])


def check_mbg_lantime_ng_power(item: str, section: Section) -> CheckResult:
    power_states = {
        "0": (State.CRIT, "not available"),
        "1": (State.CRIT, "down"),
        "2": (State.OK, "up"),
    }
    for index, power_status in section:
        if item == index:
            power_state, power_state_name = power_states[power_status]
            yield Result(state=power_state, summary=f"Status: {power_state_name}")
            return


def parse_mbg_lantime_ng_power(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_mbg_lantime_ng_power = SimpleSNMPSection(
    name="mbg_lantime_ng_power",
    detect=DETECT_MBG_LANTIME_NG,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.5597.30.0.5.0.2.1",
        oids=["1", "2"],
    ),
    parse_function=parse_mbg_lantime_ng_power,
)


check_plugin_mbg_lantime_ng_power = CheckPlugin(
    name="mbg_lantime_ng_power",
    service_name="Power Supply %s",
    discovery_function=discover_mbg_lantime_ng_power,
    check_function=check_mbg_lantime_ng_power,
)
