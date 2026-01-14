#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# Author: Lars Michelsen <lm@mathias-kettner.de>

# General Status:
# '.1.3.6.1.4.1.232.22.2.3.1.1.1.5'  => 'cpqRackCommonEnclosurePartNumber',
# '.1.3.6.1.4.1.232.22.2.3.1.1.1.6'  => 'cpqRackCommonEnclosureSparePartNumber',
# '.1.3.6.1.4.1.232.22.2.3.1.1.1.7'  => 'cpqRackCommonEnclosureSerialNum',
# '.1.3.6.1.4.1.232.22.2.3.1.1.1.8'  => 'cpqRackCommonEnclosureFWRev',
# '.1.3.6.1.4.1.232.22.2.3.1.1.1.16' => 'cpqRackCommonEnclosureCondition',


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.hp_blade.lib import DETECT_HP_BLADE

check_info = {}

# GENERAL MAPS:

hp_blade_status_map = {1: "Other", 2: "Ok", 3: "Degraded", 4: "Failed"}
hp_blade_status2nagios_map = {
    "Other": 2,
    "Ok": 0,
    "Degraded": 1,
    "Failed": 2,
}


def discover_hp_blade_general(info):
    if len(info) > 0 and len(info[0]) > 1:
        return [(None, None)]
    return []


def check_hp_blade_general(item, params, info):
    snmp_state = hp_blade_status_map[int(info[0][1])]
    status = hp_blade_status2nagios_map[snmp_state]
    return (
        status,
        f"General Status is {snmp_state} (Firmware: {info[0][0]}, S/N: {info[0][2]})",
    )


def parse_hp_blade(string_table: StringTable) -> StringTable:
    return string_table


check_info["hp_blade"] = LegacyCheckDefinition(
    name="hp_blade",
    parse_function=parse_hp_blade,
    detect=DETECT_HP_BLADE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.232.22.2.3.1.1.1",
        oids=["8", "16", "7"],
    ),
    service_name="General Status",
    discovery_function=discover_hp_blade_general,
    check_function=check_hp_blade_general,
)
