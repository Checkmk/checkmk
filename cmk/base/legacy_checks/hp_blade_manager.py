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

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition, LegacyCheckResult
from cmk.agent_based.v2 import DiscoveryResult, Service, SNMPTree, StringTable
from cmk.plugins.lib.hp import DETECT_HP_BLADE

check_info = {}

# GENERAL MAPS:

hp_blade_present_map = {1: "other", 2: "absent", 3: "present"}
hp_blade_status_map = {1: "Other", 2: "Ok", 3: "Degraded", 4: "Failed"}
hp_blade_role_map = {1: "standby", 2: "active"}

hp_blade_status2nagios_map = {
    "Other": 2,
    "Ok": 0,
    "Degraded": 1,
    "Failed": 2,
}


def discover_hp_blade_manager(string_table: StringTable) -> DiscoveryResult:
    # FIXME: Check if the implementation of the condition is correct or again a wrong implemented value
    # => if hp_blade_present_map[int(line[1])] == 'present'
    yield from (Service(item=line[0], parameters={"role": line[3]}) for line in string_table)


def check_hp_blade_manager(
    item: str, params: Mapping[str, str], string_table: StringTable
) -> LegacyCheckResult:
    for line in string_table:
        if line[0] == item:
            expected_role = params["role"]
            if line[3] != expected_role:
                yield (
                    2,
                    f"Unexpected role: {hp_blade_role_map[int(line[3])]} (Expected: {hp_blade_role_map[int(expected_role)]})",
                )
                return

            # The SNMP answer is not fully compatible to the MIB file. The value of 0 will
            # be set to "fake OK" to display the other gathered information.
            state = 2 if int(line[2]) == 0 else int(line[2])

            snmp_state = hp_blade_status_map[state]
            status = hp_blade_status2nagios_map[snmp_state]
            yield (
                status,
                f"Enclosure Manager condition is {snmp_state} (Role: {hp_blade_role_map[int(line[3])]}, S/N: {line[4]})",
            )
            return


def parse_hp_blade_manager(string_table: StringTable) -> StringTable:
    return string_table


check_info["hp_blade_manager"] = LegacyCheckDefinition(
    name="hp_blade_manager",
    parse_function=parse_hp_blade_manager,
    detect=DETECT_HP_BLADE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.232.22.2.3.1.6.1",
        oids=["3", "10", "12", "9", "8"],
    ),
    service_name="Manager %s",
    discovery_function=discover_hp_blade_manager,
    check_function=check_hp_blade_manager,
    check_default_parameters={},
)
