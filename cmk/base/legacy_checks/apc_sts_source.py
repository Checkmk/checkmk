#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# .1.3.6.1.4.1.705.2.3.5.0 2 --> MG-SNMP-STS-MIB::stsmgSource1Used.0
# .1.3.6.1.4.1.705.2.4.5.0 1 --> MG-SNMP-STS-MIB::stsmgSource2Used.0


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import contains, SNMPTree, StringTable


def inventory_apc_sts_source(info):
    if info:
        yield None, {"source1": info[0][0], "source2": info[0][1]}


def check_apc_sts_source(_not_item, params, info):
    states = {
        "1": "in use",
        "2": "not used",
    }
    sources = {}
    sources["source1"], sources["source2"] = info[0]
    for name, what in [("Source 1", "source1"), ("Source 2", "source2")]:
        state = 0
        infotext = f"{name}: {states[sources[what]]}"
        if params[what] != sources[what]:
            state = 1
            infotext += " (State has changed)"
        yield state, infotext


def parse_apc_sts_source(string_table: StringTable) -> StringTable:
    return string_table


check_info["apc_sts_source"] = LegacyCheckDefinition(
    parse_function=parse_apc_sts_source,
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.705.2.2"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.705.2",
        oids=["3.5", "4.5"],
    ),
    service_name="Source",
    discovery_function=inventory_apc_sts_source,
    check_function=check_apc_sts_source,
)
