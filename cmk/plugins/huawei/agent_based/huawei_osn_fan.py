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
from cmk.plugins.huawei.lib import DETECT_HUAWEI_OSN

_TRANSLATE_SPEED: dict[str, tuple[State, str]] = {
    "0": (State.WARN, "stop"),
    "1": (State.OK, "low"),
    "2": (State.OK, "mid-low"),
    "3": (State.OK, "mid"),
    "4": (State.OK, "mid-high"),
    "5": (State.WARN, "high"),
}


def discover_huawei_osn_fan(section: StringTable) -> DiscoveryResult:
    for line in section:
        yield Service(item=line[0])


def check_huawei_osn_fan(item: str, section: StringTable) -> CheckResult:
    for line in section:
        if item == line[0]:
            state, state_readable = _TRANSLATE_SPEED[line[1]]
            yield Result(state=state, summary=f"Speed: {state_readable}")
            return


def parse_huawei_osn_fan(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_huawei_osn_fan = SimpleSNMPSection(
    name="huawei_osn_fan",
    detect=DETECT_HUAWEI_OSN,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2011.2.25.4.70.20.10.10.1",
        oids=["1", "2"],
    ),
    parse_function=parse_huawei_osn_fan,
)


check_plugin_huawei_osn_fan = CheckPlugin(
    name="huawei_osn_fan",
    service_name="Unit %s (Fan)",
    discovery_function=discover_huawei_osn_fan,
    check_function=check_huawei_osn_fan,
)
