#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

from collections.abc import Sequence

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.genua.lib import DETECT_GENUA

# Example Agent Output:
# GENUA-MIB:

# .1.3.6.1.4.1.3137.2.1.2.1.2.9 = STRING: "carp0"
# .1.3.6.1.4.1.3137.2.1.2.1.2.10 = STRING: "carp1"
# .1.3.6.1.4.1.3137.2.1.2.1.4.9 = INTEGER: 2
# .1.3.6.1.4.1.3137.2.1.2.1.4.10 = INTEGER: 2
# .1.3.6.1.4.1.3137.2.1.2.1.7.9 = INTEGER: 2
# .1.3.6.1.4.1.3137.2.1.2.1.7.10 = INTEGER: 2


def inventory_genua_carp(section: Sequence[StringTable]) -> DiscoveryResult:
    inventory = []

    # remove empty elements due to two alternative enterprise ids in snmp_info
    section = [_f for _f in section if _f]

    if section and section[0]:
        for ifName, _ifLinkState, ifCarpState in section[0]:
            if ifCarpState in ["0", "1", "2"]:
                inventory.append((ifName, None))
    yield from [Service(item=item, parameters=parameters) for (item, parameters) in inventory]


def genua_linkstate(st):
    names = {
        "0": "unknown",
        "1": "down",
        "2": "up",
        "3": "hd",
        "4": "fd",
    }
    return names.get(st, st)


def genua_carpstate(st):
    names = {
        "0": "init",
        "1": "backup",
        "2": "master",
    }
    return names.get(st, st)


def check_genua_carp(item: str, section: Sequence[StringTable]) -> CheckResult:
    # remove empty elements due to two alternative enterprise ids in snmp_info
    section = [_f for _f in section if _f]

    if not section[0]:
        yield Result(state=State.UNKNOWN, summary="Invalid Output from Agent")
        return
    state = 0
    nodes = len(section)
    masters = 0
    output = ""
    if nodes > 1:
        prefix = "Cluster test: "
    else:
        prefix = "Node test: "

    # Loop over all nodes, just one line if not a cluster
    for line in section:
        # Loop over interfaces on node
        for ifName, ifLinkState, ifCarpState in line:
            ifLinkStateStr = genua_linkstate(str(ifLinkState))
            ifCarpStateStr = genua_carpstate(str(ifCarpState))
            # is inventorized interface in state carp master ?
            if ifName == item and ifCarpState == "2":
                # is master
                masters += 1
                if masters == 1:
                    if nodes > 1:
                        output = "one "
                    output += (
                        f"node in carp state {ifCarpStateStr} with IfLinkState {ifLinkStateStr}"
                    )
                    # first master
                    if ifLinkState == "2":
                        state = 0
                    elif ifLinkState == "1":
                        state = 2
                    elif ifLinkState in ["0", "3"]:
                        state = 1
                    else:
                        state = 3
                else:
                    state = 2
                    output = f"{masters} nodes in carp state {ifCarpStateStr} on cluster with {nodes} nodes"
            # look for non-masters, only interesting if no cluster
            elif ifName == item and nodes == 1:
                output = f"node in carp state {ifCarpStateStr} with IfLinkState {ifLinkStateStr}"
                # carp backup
                if ifCarpState == "1" and ifLinkState == "1":
                    state = 0
                else:
                    state = 1

    # no masters found in cluster
    if nodes > 1 and masters == 0:
        state = 2
        output = f"No master found on cluster with {nodes} nodes"

    output = prefix + output
    yield Result(state=State(state), summary=output)
    return


def parse_genua_carp(string_table: Sequence[StringTable]) -> Sequence[StringTable]:
    return string_table


snmp_section_genua_carp = SNMPSection(
    name="genua_carp",
    detect=DETECT_GENUA,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.3137.2.1.2.1",
            oids=["2", "4", "7"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.3717.2.1.2.1",
            oids=["2", "4", "7"],
        ),
    ],
    parse_function=parse_genua_carp,
)


check_plugin_genua_carp = CheckPlugin(
    name="genua_carp",
    service_name="Carp Interface %s",
    discovery_function=inventory_genua_carp,
    check_function=check_genua_carp,
)
