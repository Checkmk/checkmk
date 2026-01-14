#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.f5_bigip.lib import F5_BIGIP

check_info = {}

# Agent / MIB output
# SysChassisPowerSupplyEntry ::=
#        SEQUENCE {
#                sysChassisPowerSupplyIndex                   INTEGER,
#                sysChassisPowerSupplyStatus                  INTEGER
#        }

# sysChassisPowerSupplyStatus
#   bad(0),
#   good(1),
#   notpresent(2)


def discover_f5_bigip_psu(info):
    inventory = []
    for line in info:
        psu = line[0]
        state = line[1]
        # inventorize the PSU unless it's in state 2 (notpresent)
        if state != "2":
            inventory.append((psu, None))
    return inventory


def check_f5_bigip_psu(item, _no_params, info):
    for line in info:
        psu = line[0]
        state = int(line[1])
        if psu == item:
            if state == 1:
                return (0, "PSU state: good")
            if state == 0:
                return (2, "PSU state: bad!!")
            if state == 2:
                return (1, "PSU state: notpresent!")
            return (3, "PSU state is unknown")

    return (3, "item not found in SNMP output")


def parse_f5_bigip_psu(string_table: StringTable) -> StringTable:
    return string_table


check_info["f5_bigip_psu"] = LegacyCheckDefinition(
    name="f5_bigip_psu",
    parse_function=parse_f5_bigip_psu,
    detect=F5_BIGIP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3375.2.1.3.2.2.2.1",
        oids=["1", "2"],
    ),
    service_name="PSU %s",
    # Get ID and status from the SysChassisPowerSupplyTable,
    discovery_function=discover_f5_bigip_psu,
    check_function=check_f5_bigip_psu,
)
