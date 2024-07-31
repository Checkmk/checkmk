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


def inventory_dell_chassis_kvm(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


def check_dell_chassis_kvm(section: StringTable) -> CheckResult:
    state_table = {
        "1": ("other, ", State.WARN),
        "2": ("unknown, ", State.WARN),
        "3": ("normal", State.OK),
        "4": ("nonCritical, ", State.WARN),
        "5": ("Critical, ", State.CRIT),
        "6": ("NonRecoverable, ", State.CRIT),
    }
    infotext, state = state_table.get(section[0][0], ("unknown state", State.UNKNOWN))

    yield Result(state=state, summary=f"Status: {infotext}")
    yield Result(state=State.OK, summary=f"Firmware: {section[0][1]}")


def parse_dell_chassis_kvm(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_dell_chassis_kvm = SimpleSNMPSection(
    name="dell_chassis_kvm",
    detect=DETECT_CHASSIS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.674.10892.2",
        oids=["3.1.2", "1.2.2"],
    ),
    parse_function=parse_dell_chassis_kvm,
)
check_plugin_dell_chassis_kvm = CheckPlugin(
    name="dell_chassis_kvm",
    service_name="Overall KVM Status",
    discovery_function=inventory_dell_chassis_kvm,
    check_function=check_dell_chassis_kvm,
)
