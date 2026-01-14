#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# Author: Lars Michelsen <lm@mathias-kettner.de>

# FAN:
# '.1.3.6.1.4.1.232.22.2.3.1.3.1.3'  => 'cpqRackCommonEnclosureFanIndex',
# '.1.3.6.1.4.1.232.22.2.3.1.3.1.6'  => 'cpqRackCommonEnclosureFanPartNumber',
# '.1.3.6.1.4.1.232.22.2.3.1.3.1.7'  => 'cpqRackCommonEnclosureFanSparePartNumber',
# '.1.3.6.1.4.1.232.22.2.3.1.3.1.8'  => 'cpqRackCommonEnclosureFanPresent',
# '.1.3.6.1.4.1.232.22.2.3.1.3.1.11' => 'cpqRackCommonEnclosureFanCondition',


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.hp_blade.lib import DETECT_HP_BLADE

check_info = {}

# GENERAL MAPS:

hp_blade_present_map = {1: "other", 2: "absent", 3: "present"}
hp_blade_status_map = {1: "Other", 2: "Ok", 3: "Degraded", 4: "Failed"}

hp_blade_status2nagios_map = {
    "Other": 2,
    "Ok": 0,
    "Degraded": 1,
    "Failed": 2,
}


def discover_hp_blade_fan(info):
    return [(line[0], None) for line in info if hp_blade_present_map[int(line[1])] == "present"]


def check_hp_blade_fan(item, params, info):
    for line in info:
        if line[0] == item:
            present_state = hp_blade_present_map[int(line[1])]
            if present_state != "present":
                return (
                    2,
                    "FAN was present but is not available anymore"
                    " (Present state: %s)" % present_state,
                )

            snmp_state = hp_blade_status_map[int(line[2])]
            status = hp_blade_status2nagios_map[snmp_state]
            return (status, "FAN condition is %s" % (snmp_state))
    return (3, "item not found in snmp data")


def parse_hp_blade_fan(string_table: StringTable) -> StringTable:
    return string_table


check_info["hp_blade_fan"] = LegacyCheckDefinition(
    name="hp_blade_fan",
    parse_function=parse_hp_blade_fan,
    detect=DETECT_HP_BLADE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.232.22.2.3.1.3.1",
        oids=["3", "8", "11"],
    ),
    service_name="FAN %s",
    discovery_function=discover_hp_blade_fan,
    check_function=check_hp_blade_fan,
)
