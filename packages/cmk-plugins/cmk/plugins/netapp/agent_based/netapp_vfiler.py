#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# netappFiler(1) vfiler(16) vfTable (3) vfEntry (1) vfName (2)
#                                                   vfState(9)


from cmk.agent_based.v2 import (
    all_of,
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)


def discover_netapp_vfiler(section: StringTable) -> DiscoveryResult:
    for line in section:
        # If we find an entry consisting of name and status, add it to inventory.
        # otherwise we don't inventorize anything.
        if len(line) == 2:
            yield Service(item=line[0])


def check_netapp_vfiler(item: str, section: StringTable) -> CheckResult:
    for vfEntry in section:
        vfName, vfState = vfEntry
        if vfName == item:
            if vfState == "2":
                yield Result(state=State.OK, summary="vFiler is running")
                return
            if vfState == "1":
                yield Result(state=State.CRIT, summary="vFiler is stopped")
                return
            yield Result(state=State.UNKNOWN, summary="UNKOWN - vFiler status unknown")
            return
    yield Result(state=State.UNKNOWN, summary="vFiler not found in SNMP output")
    return


def parse_netapp_vfiler(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_netapp_vfiler = SimpleSNMPSection(
    name="netapp_vfiler",
    detect=all_of(
        contains(".1.3.6.1.2.1.1.1.0", "netapp release"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.789"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.789.1.16.3.1",
        oids=["2", "9"],
    ),
    parse_function=parse_netapp_vfiler,
)


check_plugin_netapp_vfiler = CheckPlugin(
    name="netapp_vfiler",
    service_name="vFiler Status %s",
    discovery_function=discover_netapp_vfiler,
    check_function=check_netapp_vfiler,
)
