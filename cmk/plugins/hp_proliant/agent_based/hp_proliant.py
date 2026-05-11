#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# .1.3.6.1.4.1.232.11.1.3.0  1
# .1.3.6.1.4.1.232.11.2.14.1.1.5.0  "2009.05.18"
# .1.3.6.1.4.1.232.2.2.2.1.0  "GB8851CPPH


from cmk.agent_based.v2 import (
    all_of,
    any_of,
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    exists,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)

_MAP_STATES = {
    "1": (State.UNKNOWN, "unknown"),
    "2": (State.OK, "OK"),
    "3": (State.WARN, "degraded"),
    "4": (State.CRIT, "failed"),
}


def parse_hp_proliant(string_table: StringTable) -> StringTable:
    return string_table


def discover_proliant_general(section: StringTable) -> DiscoveryResult:
    if section and len(section[0]) > 1 and section[0][0]:
        yield Service()


def check_proliant_general(section: StringTable) -> CheckResult:
    if not section:
        return

    status, firmware, serial_number = section[0]
    state, state_readable = _MAP_STATES.get(status, (State.UNKNOWN, f"unhandled[{status}]"))
    yield Result(
        state=state,
        summary=f"Status: {state_readable}, Firmware: {firmware}, S/N: {serial_number}",
    )


snmp_section_hp_proliant = SimpleSNMPSection(
    name="hp_proliant",
    detect=any_of(
        contains(".1.3.6.1.2.1.1.2.0", "8072.3.2.10"),
        contains(".1.3.6.1.2.1.1.2.0", "232.9.4.10"),
        all_of(
            contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.311.1.1.3.1.2"),
            exists(".1.3.6.1.4.1.232.11.1.3.0"),
        ),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.232",
        oids=["11.1.3.0", "11.2.14.1.1.5.0", "2.2.2.1.0"],
    ),
    parse_function=parse_hp_proliant,
)


check_plugin_hp_proliant = CheckPlugin(
    name="hp_proliant",
    service_name="General Status",
    discovery_function=discover_proliant_general,
    check_function=check_proliant_general,
)
