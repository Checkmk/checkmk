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
from cmk.plugins.lib.dell import DETECT_CHASSIS


def inventory_dell_chassis_fans(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


def check_dell_chassis_fans(section: StringTable) -> CheckResult:
    state_table = {
        "1": ("other, ", State.WARN),
        "2": ("unknown, ", State.WARN),
        "3": ("normal", State.OK),
        "4": ("nonCritical, ", State.WARN),
        "5": ("Critical, ", State.CRIT),
        "6": ("NonRecoverable, ", State.CRIT),
    }
    infotext, state = state_table.get(section[0][0], ("unknown state", State.CRIT))

    infotext = "Status: " + infotext

    yield Result(state=state, summary=infotext)


def parse_dell_chassis_fans(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_dell_chassis_fans = SimpleSNMPSection(
    name="dell_chassis_fans",
    detect=DETECT_CHASSIS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.674.10892.2.3.1",
        oids=["6"],
    ),
    parse_function=parse_dell_chassis_fans,
)
check_plugin_dell_chassis_fans = CheckPlugin(
    name="dell_chassis_fans",
    service_name="Overall Fan Status",
    discovery_function=inventory_dell_chassis_fans,
    check_function=check_dell_chassis_fans,
)
