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


def inventory_dell_chassis_status(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


def check_dell_chassis_status(section: StringTable) -> CheckResult:
    whats = [
        "URL",
        "Locaction",
        "Name",
        "Service Tag",
        "Data Center",
        "Firmware Version",
        "Status",
    ]

    state_table = {
        "1": ("Other, ", State.WARN),
        "2": ("Unknown, ", State.WARN),
        "3": ("OK", State.OK),
        "4": ("Non-Critical, ", State.WARN),
        "5": ("Critical, ", State.CRIT),
        "6": ("Non-Recoverable, ", State.CRIT),
    }

    for what, value in zip(whats, section[0]):
        if what == "Status":
            descr, status = state_table[value]
            yield Result(state=status, summary=what + ": " + descr)
        else:
            yield Result(state=State.OK, summary=what + ": " + value)


def parse_dell_chassis_status(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_dell_chassis_status = SimpleSNMPSection(
    name="dell_chassis_status",
    detect=DETECT_CHASSIS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.674.10892.2",
        oids=["1.1.7", "1.1.9", "1.1.10", "1.1.11", "1.1.15", "1.2.1", "2.1"],
    ),
    parse_function=parse_dell_chassis_status,
)
check_plugin_dell_chassis_status = CheckPlugin(
    name="dell_chassis_status",
    service_name="Chassis Health",
    discovery_function=inventory_dell_chassis_status,
    check_function=check_dell_chassis_status,
)
