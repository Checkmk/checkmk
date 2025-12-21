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


def inventory_genua_state(section: Sequence[StringTable]) -> DiscoveryResult:
    # remove empty elements due to two alternative enterprise ids in snmp_info
    section = [_f for _f in section if _f]
    if section and section[0]:
        numifs = 0
        for _ifIndex, _ifName, _ifType, _ifLinkState, ifCarpState in section[0]:
            if ifCarpState in ["0", "1", "2"]:
                numifs += 1
        # inventorize only if we find at least two carp interfaces
        if numifs > 1:
            yield Service()


def genua_state_str(st):
    names = {
        "0": "init",
        "1": "backup",
        "2": "master",
    }
    return names.get(st, st)


def check_genua_state(section: Sequence[StringTable]) -> CheckResult:
    # remove empty elements due to two alternative enterprise ids in snmp_info
    section = [_f for _f in section if _f]
    if not section[0]:
        yield Result(state=State.UNKNOWN, summary="Invalid Output from Agent")
        return

    state = 0
    carp_info = []

    for ifIndex, ifName, ifType, ifLinkState, ifCarpState in section[0]:
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
        output += f":{carp_states[int(i)]} "

    yield Result(state=State(state), summary=output)
    return


def parse_genua_state_correlation(string_table: Sequence[StringTable]) -> Sequence[StringTable]:
    return string_table


snmp_section_genua_state_correlation = SNMPSection(
    name="genua_state_correlation",
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
    parse_function=parse_genua_state_correlation,
)


check_plugin_genua_state_correlation = CheckPlugin(
    name="genua_state_correlation",
    service_name="Carp Correlation",
    discovery_function=inventory_genua_state,
    check_function=check_genua_state,
)
