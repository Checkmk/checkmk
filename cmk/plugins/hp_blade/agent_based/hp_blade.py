#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Author: Lars Michelsen <lm@mathias-kettner.de>

# General Status:
# '.1.3.6.1.4.1.232.22.2.3.1.1.1.5'  => 'cpqRackCommonEnclosurePartNumber',
# '.1.3.6.1.4.1.232.22.2.3.1.1.1.6'  => 'cpqRackCommonEnclosureSparePartNumber',
# '.1.3.6.1.4.1.232.22.2.3.1.1.1.7'  => 'cpqRackCommonEnclosureSerialNum',
# '.1.3.6.1.4.1.232.22.2.3.1.1.1.8'  => 'cpqRackCommonEnclosureFWRev',
# '.1.3.6.1.4.1.232.22.2.3.1.1.1.16' => 'cpqRackCommonEnclosureCondition',


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
from cmk.plugins.hp_blade.lib import DETECT_HP_BLADE

_STATUS_MAP: dict[int, tuple[State, str]] = {
    1: (State.CRIT, "Other"),
    2: (State.OK, "Ok"),
    3: (State.WARN, "Degraded"),
    4: (State.CRIT, "Failed"),
}


def parse_hp_blade(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_hp_blade = SimpleSNMPSection(
    name="hp_blade",
    detect=DETECT_HP_BLADE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.232.22.2.3.1.1.1",
        oids=["8", "16", "7"],
    ),
    parse_function=parse_hp_blade,
)


def discover_hp_blade_general(section: StringTable) -> DiscoveryResult:
    if section and len(section[0]) > 1:
        yield Service()


def check_hp_blade_general(section: StringTable) -> CheckResult:
    firmware, raw_state, serial = section[0]
    state, state_readable = _STATUS_MAP[int(raw_state)]
    yield Result(
        state=state,
        summary=f"General Status is {state_readable} (Firmware: {firmware}, S/N: {serial})",
    )


check_plugin_hp_blade = CheckPlugin(
    name="hp_blade",
    service_name="General Status",
    discovery_function=discover_hp_blade_general,
    check_function=check_hp_blade_general,
)
