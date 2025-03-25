#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import DiscoveryResult, Service, SNMPTree, StringTable
from cmk.plugins.lib.genua import DETECT_GENUA

check_info = {}

# Example Agent Output:
# GENUA-MIB:
# .1.3.6.1.4.1.3717.2.1.1.6.1 = INTEGER: 300000
# .1.3.6.1.4.1.3717.2.1.1.6.2 = INTEGER: 1268
# .1.3.6.1.4.1.3717.2.1.1.6.3 = INTEGER: 1


def saveint(i: str) -> int:
    """Tries to cast a string to an integer and return it. In case this
    fails, it returns 0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0 back from this function,
    you can not know whether it is really 0 or something went wrong."""
    try:
        return int(i)
    except (TypeError, ValueError):
        return 0


def discover_genua_pfstate(string_table: StringTable) -> DiscoveryResult:
    # remove empty elements due to alternative enterprise id in snmp_info
    string_table = [_f for _f in string_table if _f]

    if string_table and string_table[0] and len(string_table[0][0]) == 3:
        yield Service()


def pfstate(st):
    names = {
        "0": "notOK",
        "1": "OK",
        "2": "unknown",
    }
    return names.get(st, st)


def check_genua_pfstate(item, params, info):
    # remove empty elements due to alternative enterprise id in snmp_info
    info = [_f for _f in info if _f]

    if info[0] and len(info[0][0]) == 3:
        pfstateMax = saveint(info[0][0][0])
        pfstateUsed = saveint(info[0][0][1])
        pfstateStatus = info[0][0][2]
    else:
        yield 3, "Invalid Output from Agent"
        return

    pfstatus = pfstate(str(pfstateStatus))
    yield (
        0 if pfstateStatus == "1" else 1,
        f"PF State: {pfstatus}",
    )

    yield check_levels(
        pfstateUsed,
        "statesused",
        params["used"],
        human_readable_func=str,
        infoname="States used",
        boundaries=(0, pfstateMax),
    )

    yield 0, f"States max: {pfstateMax}"


def parse_genua_pfstate(string_table: Sequence[StringTable]) -> Sequence[StringTable]:
    return string_table


check_info["genua_pfstate"] = LegacyCheckDefinition(
    name="genua_pfstate",
    parse_function=parse_genua_pfstate,
    detect=DETECT_GENUA,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.3717.2.1.1.6",
            oids=["1", "2", "3"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.3137.2.1.1.6",
            oids=["1", "2", "3"],
        ),
    ],
    service_name="Paketfilter Status",
    discovery_function=discover_genua_pfstate,
    check_function=check_genua_pfstate,
    check_ruleset_name="pf_used_states",
    check_default_parameters={"used": None},
)
