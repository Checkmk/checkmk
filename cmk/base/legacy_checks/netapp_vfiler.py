#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# netappFiler(1) vfiler(16) vfTable (3) vfEntry (1) vfName (2)
#                                                   vfState(9)


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import all_of, contains, SNMPTree, startswith, StringTable

check_info = {}


def discover_netapp_vfiler(info):
    inventory = []
    for line in info:
        # If we find an entry consisting of name and status, add it to inventory.
        # otherwise we don't inventorize anything.
        if len(line) == 2:
            inventory.append((line[0], None))

    return inventory


def check_netapp_vfiler(item, _no_params, info):
    for vfEntry in info:
        vfName, vfState = vfEntry
        if vfName == item:
            if vfState == "2":
                return (0, "vFiler is running")
            if vfState == "1":
                return (2, "vFiler is stopped")
            return (3, "UNKOWN - vFiler status unknown")
    return (3, "vFiler not found in SNMP output")


def parse_netapp_vfiler(string_table: StringTable) -> StringTable:
    return string_table


check_info["netapp_vfiler"] = LegacyCheckDefinition(
    name="netapp_vfiler",
    parse_function=parse_netapp_vfiler,
    detect=all_of(
        contains(".1.3.6.1.2.1.1.1.0", "netapp release"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.789"),
    ),
    # get the vfName and vfState from the vfEntry table
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.789.1.16.3.1",
        oids=["2", "9"],
    ),
    service_name="vFiler Status %s",
    discovery_function=discover_netapp_vfiler,
    check_function=check_netapp_vfiler,
)
