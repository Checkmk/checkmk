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

# .1.3.6.1.4.1.3137.2.1.2.1.1.9 = INTEGER: 9
# .1.3.6.1.4.1.3137.2.1.2.1.1.10 = INTEGER: 10
# .1.3.6.1.4.1.3137.2.1.2.1.2.9 = STRING: "carp0"
# .1.3.6.1.4.1.3137.2.1.2.1.2.10 = STRING: "carp1"
# .1.3.6.1.4.1.3137.2.1.2.1.3.9 = INTEGER: 5
# .1.3.6.1.4.1.3137.2.1.2.1.3.10 = INTEGER: 5
# .1.3.6.1.4.1.3137.2.1.2.1.4.9 = INTEGER: 2
# .1.3.6.1.4.1.3137.2.1.2.1.4.10 = INTEGER: 2
# .1.3.6.1.4.1.3137.2.1.2.1.7.9 = INTEGER: 2
# .1.3.6.1.4.1.3137.2.1.2.1.7.10 = INTEGER: 2


def inventory_genua_state(info):
    # remove empty elements due to two alternative enterprise ids in snmp_info
    info = [_f for _f in info if _f]
    if info and info[0]:
        numifs = 0
        for _ifIndex, _ifName, _ifType, _ifLinkState, ifCarpState in info[0]:
            if ifCarpState in ["0", "1", "2"]:
                numifs += 1
        # inventorize only if we find at least two carp interfaces
        if numifs > 1:
            return [(None, None)]
    return None


def genua_state_str(st):
    names = {
        "0": "init",
        "1": "backup",
        "2": "master",
    }
    return names.get(st, st)


def check_genua_state(item, _no_params, info):
    # remove empty elements due to two alternative enterprise ids in snmp_info
    info = [_f for _f in info if _f]
    if not info[0]:
        return (3, "Invalid Output from Agent")

    state = 0
    carp_info = []

    for ifIndex, ifName, ifType, ifLinkState, ifCarpState in info[0]:
        if ifType == "6":
            carp_info.append((ifIndex, ifName, ifType, ifLinkState, ifCarpState))

    # critical if the carp interfaces dont have the same state
    carp_states = [0, 0, 0]
    for elem in carp_info:
        carp_states[int(elem[4])] += 1
        if carp_info[0][4] != elem[4]:
            state = 2

    output = "Number of carp IFs in states "
    for i in ("0", "1", "2"):
        output += genua_state_str(i)
        output += ":%d " % carp_states[int(i)]

    return (state, output)


def parse_genua_state_correlation(string_table: Sequence[StringTable]) -> Sequence[StringTable]:
    return string_table


check_info["genua_state_correlation"] = LegacyCheckDefinition(
    name="genua_state_correlation",
    parse_function=parse_genua_state_correlation,
    detect=DETECT_GENUA,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.3717.2.1.2.1",
            oids=["1", "2", "3", "4", "7"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.3137.2.1.2.1",
            oids=["1", "2", "3", "4", "7"],
        ),
    ],
    service_name="Carp Correlation",
    discovery_function=inventory_genua_state,
    check_function=check_genua_state,
)
