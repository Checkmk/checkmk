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
from cmk.plugins.lib.avaya import DETECT_AVAYA

avaya_chassis_ps_status_codes = {
    1: (State.UNKNOWN, "unknown", "Status cannot be determined"),
    2: (State.WARN, "empty", "Power supply not installed"),
    3: (State.OK, "up", "Present and supplying power"),
    4: (State.CRIT, "down", "Failure indicated"),
}


def inventory_avaya_chassis_ps(section: StringTable) -> DiscoveryResult:
    for line in section:
        # Discover only installed power supplies
        if line[1] != "2":
            yield Service(item=line[0])


def check_avaya_chassis_ps(item: str, section: StringTable) -> CheckResult:
    for line in section:
        if line[0] == item:
            ps_status_code = int(line[1])

    status, status_name, description = avaya_chassis_ps_status_codes[ps_status_code]
    yield Result(state=status, summary=f"{description} ({status_name})")


def parse_avaya_chassis_ps(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_avaya_chassis_ps = SimpleSNMPSection(
    name="avaya_chassis_ps",
    detect=DETECT_AVAYA,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2272.1.4.8.1.1",
        oids=["1", "2"],
    ),
    parse_function=parse_avaya_chassis_ps,
)
check_plugin_avaya_chassis_ps = CheckPlugin(
    name="avaya_chassis_ps",
    service_name="Power Supply %s",
    discovery_function=inventory_avaya_chassis_ps,
    check_function=check_avaya_chassis_ps,
)
