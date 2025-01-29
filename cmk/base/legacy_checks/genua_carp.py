#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.genua import DETECT_GENUA

check_info = {}

# Example Agent Output:
# GENUA-MIB:

# .1.3.6.1.4.1.3137.2.1.2.1.2.9 = STRING: "carp0"
# .1.3.6.1.4.1.3137.2.1.2.1.2.10 = STRING: "carp1"
# .1.3.6.1.4.1.3137.2.1.2.1.4.9 = INTEGER: 2
# .1.3.6.1.4.1.3137.2.1.2.1.4.10 = INTEGER: 2
# .1.3.6.1.4.1.3137.2.1.2.1.7.9 = INTEGER: 2
# .1.3.6.1.4.1.3137.2.1.2.1.7.10 = INTEGER: 2


def inventory_genua_carp(info):
    inventory = []

    # remove empty elements due to two alternative enterprise ids in snmp_info
    info = [_f for _f in info if _f]

    if info and info[0]:
        for ifName, _ifLinkState, ifCarpState in info[0]:
            if ifCarpState in ["0", "1", "2"]:
                inventory.append((ifName, None))
    return inventory


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


def check_genua_carp(item, _no_params, info):
    # remove empty elements due to two alternative enterprise ids in snmp_info
    info = [_f for _f in info if _f]

    if not info[0]:
        return (3, "Invalid Output from Agent")
    state = 0
    nodes = len(info)
    masters = 0
    output = ""
    if nodes > 1:
        prefix = "Cluster test: "
    else:
        prefix = "Node test: "

    # Loop over all nodes, just one line if not a cluster
    for line in info:
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
                    output = "%d nodes in carp state %s on cluster with %d nodes" % (
                        masters,
                        ifCarpStateStr,
                        nodes,
                    )
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
        output = "No master found on cluster with %d nodes" % nodes

    output = prefix + output
    return (state, output)


def parse_genua_carp(string_table: Sequence[StringTable]) -> Sequence[StringTable]:
    return string_table


check_info["genua_carp"] = LegacyCheckDefinition(
    name="genua_carp",
    parse_function=parse_genua_carp,
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
    service_name="Carp Interface %s",
    discovery_function=inventory_genua_carp,
    check_function=check_genua_carp,
)
