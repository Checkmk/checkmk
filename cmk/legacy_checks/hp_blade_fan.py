#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Author: Lars Michelsen <lm@mathias-kettner.de>

# FAN:
# '.1.3.6.1.4.1.232.22.2.3.1.3.1.3'  => 'cpqRackCommonEnclosureFanIndex',
# '.1.3.6.1.4.1.232.22.2.3.1.3.1.6'  => 'cpqRackCommonEnclosureFanPartNumber',
# '.1.3.6.1.4.1.232.22.2.3.1.3.1.7'  => 'cpqRackCommonEnclosureFanSparePartNumber',
# '.1.3.6.1.4.1.232.22.2.3.1.3.1.8'  => 'cpqRackCommonEnclosureFanPresent',
# '.1.3.6.1.4.1.232.22.2.3.1.3.1.11' => 'cpqRackCommonEnclosureFanCondition',


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

_PRESENT_MAP: dict[int, str] = {1: "other", 2: "absent", 3: "present"}

_STATUS_MAP: dict[int, tuple[State, str]] = {
    1: (State.CRIT, "Other"),
    2: (State.OK, "Ok"),
    3: (State.WARN, "Degraded"),
    4: (State.CRIT, "Failed"),
}


def parse_hp_blade_fan(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_hp_blade_fan = SimpleSNMPSection(
    name="hp_blade_fan",
    detect=DETECT_HP_BLADE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.232.22.2.3.1.3.1",
        oids=["3", "8", "11"],
    ),
    parse_function=parse_hp_blade_fan,
)


def discover_hp_blade_fan(section: StringTable) -> DiscoveryResult:
    for line in section:
        if _PRESENT_MAP[int(line[1])] == "present":
            yield Service(item=line[0])


def check_hp_blade_fan(item: str, section: StringTable) -> CheckResult:
    for line in section:
        if line[0] != item:
            continue
        present_state = _PRESENT_MAP[int(line[1])]
        if present_state != "present":
            yield Result(
                state=State.CRIT,
                summary=(
                    f"FAN was present but is not available anymore (Present state: {present_state})"
                ),
            )
            return
        state, state_readable = _STATUS_MAP[int(line[2])]
        yield Result(state=state, summary=f"FAN condition is {state_readable}")
        return


check_plugin_hp_blade_fan = CheckPlugin(
    name="hp_blade_fan",
    service_name="FAN %s",
    discovery_function=discover_hp_blade_fan,
    check_function=check_hp_blade_fan,
)
