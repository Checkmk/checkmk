#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.tplink import DETECT_TPLINK


def _parse_memory_percentage_used(string_table: StringTable) -> float | None:
    if not string_table or not string_table[0]:
        return None

    utilization_of_units = [float(line[0]) for line in string_table]
    return sum(utilization_of_units) / len(utilization_of_units)


snmp_section_memory_utilization = SimpleSNMPSection(
    parsed_section_name="memory_utilization",
    name="tplink_memory_utilization",
    detect=DETECT_TPLINK,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11863.6.4.1.2.1.1",
        oids=["2"],
    ),
    parse_function=_parse_memory_percentage_used,
)
