#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Author: Lars Michelsen <lm@mathias-kettner.de>

# Manager:
# '.1.3.6.1.4.1.232.22.2.3.1.6.1.3'  => 'cpqRackCommonEnclosureManagerIndex',
# '.1.3.6.1.4.1.232.22.2.3.1.6.1.6'  => 'cpqRackCommonEnclosureManagerPartNumber',
# '.1.3.6.1.4.1.232.22.2.3.1.6.1.7'  => 'cpqRackCommonEnclosureManagerSparePartNumber',
# '.1.3.6.1.4.1.232.22.2.3.1.6.1.8'  => 'cpqRackCommonEnclosureManagerSerialNum',
# '.1.3.6.1.4.1.232.22.2.3.1.6.1.9'  => 'cpqRackCommonEnclosureManagerRole',
# '.1.3.6.1.4.1.232.22.2.3.1.6.1.10' => 'cpqRackCommonEnclosureManagerPresent',
# '.1.3.6.1.4.1.232.22.2.3.1.6.1.12' => 'cpqRackCommonEnclosureManagerCondition',

from collections.abc import Mapping

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

_ROLE_MAP: dict[int, str] = {1: "standby", 2: "active"}


def parse_hp_blade_manager(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_hp_blade_manager = SimpleSNMPSection(
    name="hp_blade_manager",
    detect=DETECT_HP_BLADE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.232.22.2.3.1.6.1",
        oids=["3", "10", "12", "9", "8"],
    ),
    parse_function=parse_hp_blade_manager,
)


def discover_hp_blade_manager(section: StringTable) -> DiscoveryResult:
    # FIXME: Check if the implementation of the condition is correct or again a wrong implemented value
    # => if hp_blade_present_map[int(line[1])] == 'present'
    for line in section:
        yield Service(item=line[0], parameters={"role": line[3]})


def check_hp_blade_manager(
    item: str, params: Mapping[str, str], section: StringTable
) -> CheckResult:
    for line in section:
        if line[0] != item:
            continue
        expected_role = params["role"]
        if line[3] != expected_role:
            yield Result(
                state=State.CRIT,
                summary=(
                    f"Unexpected role: {_ROLE_MAP[int(line[3])]} "
                    f"(Expected: {_ROLE_MAP[int(expected_role)]})"
                ),
            )
            return

        # The SNMP answer is not fully compatible to the MIB file. The value of 0 will
        # be set to "fake OK" to display the other gathered information.
        raw_state = 2 if int(line[2]) == 0 else int(line[2])
        state, state_readable = _STATUS_MAP[raw_state]
        yield Result(
            state=state,
            summary=(
                f"Enclosure Manager condition is {state_readable} "
                f"(Role: {_ROLE_MAP[int(line[3])]}, S/N: {line[4]})"
            ),
        )
        return


check_plugin_hp_blade_manager = CheckPlugin(
    name="hp_blade_manager",
    service_name="Manager %s",
    discovery_function=discover_hp_blade_manager,
    check_function=check_hp_blade_manager,
    check_default_parameters={},
)
