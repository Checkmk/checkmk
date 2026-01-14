#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# Author: Lars Michelsen <lm@mathias-kettner.de>

# PSU:
# '.1.3.6.1.4.1.232.22.2.5.1.1.1.3'  => 'cpqRackPowerSupplyIndex',
# '.1.3.6.1.4.1.232.22.2.5.1.1.1.5'  => 'cpqRackPowerSupplySerialNum',
# '.1.3.6.1.4.1.232.22.2.5.1.1.1.6'  => 'cpqRackPowerSupplyPartNumber',
# '.1.3.6.1.4.1.232.22.2.5.1.1.1.7'  => 'cpqRackPowerSupplySparePartNumber',
# '.1.3.6.1.4.1.232.22.2.5.1.1.1.10' => 'cpqRackPowerSupplyCurPwrOutput',
# '.1.3.6.1.4.1.232.22.2.5.1.1.1.14' => 'cpqRackPowerSupplyStatus',
# '.1.3.6.1.4.1.232.22.2.5.1.1.1.15' => 'cpqRackPowerSupplyInputLineStatus',
# '.1.3.6.1.4.1.232.22.2.5.1.1.1.16' => 'cpqRackPowerSupplyPresent',
# '.1.3.6.1.4.1.232.22.2.5.1.1.1.17' => 'cpqRackPowerSupplyCondition',

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

# PSU MAPS:

hp_blade_psu_status = {
    1: "noError",
    2: "generalFailure",
    3: "bistFailure",
    4: "fanFailure",
    5: "tempFailure",
    6: "interlockOpen",
    7: "epromFailed",
    8: "vrefFailed",
    9: "dacFailed",
    10: "ramTestFailed",
    11: "voltageChannelFailed",
    12: "orringdiodeFailed",
    13: "brownOut",
    14: "giveupOnStartup",
    15: "nvramInvalid",
    16: "calibrationTableInvalid",
}

hp_blade_psu_inputline_status = {
    1: "noError",
    2: "lineOverVoltage",
    3: "lineUnderVoltage",
    4: "lineHit",
    5: "brownOut",
    6: "linePowerLoss",
}


def discover_hp_blade_psu(info):
    return [(line[0], None) for line in info if hp_blade_present_map[int(line[1])] == "present"]


def check_hp_blade_psu(item, params, info):
    for line in info:
        if line[0] == item:
            present_state = hp_blade_present_map[int(line[1])]
            if present_state != "present":
                return (
                    2,
                    "PSU was present but is not available anymore."
                    " (Present state: %s" % present_state,
                )

            snmp_state = hp_blade_status_map[int(line[2])]
            status = hp_blade_status2nagios_map[snmp_state]

            detail_output = ""
            if status == 0:
                detail_output = ", Output: %sW" % line[3]
            else:
                # FIXME: This should probably append strings, not overwrite them...
                detail_output = (" (%s)" % hp_blade_psu_status[4]) if int(line[4]) >= 1 else ""
                detail_output = (
                    (", Inputline: %s" % hp_blade_psu_inputline_status[5])
                    if int(line[5]) >= 1
                    else ""
                )

            perfdata = [("output", line[3])]

            return (
                status,
                f"PSU is {snmp_state}{detail_output} (S/N: {line[6]})",
                perfdata,
            )
    return (3, "item not found in snmp data")


def parse_hp_blade_psu(string_table: StringTable) -> StringTable:
    return string_table


check_info["hp_blade_psu"] = LegacyCheckDefinition(
    name="hp_blade_psu",
    parse_function=parse_hp_blade_psu,
    detect=DETECT_HP_BLADE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.232.22.2.5.1.1.1",
        oids=["3", "16", "17", "10", "14", "15", "5"],
    ),
    service_name="PSU %s",
    discovery_function=discover_hp_blade_psu,
    check_function=check_hp_blade_psu,
)
