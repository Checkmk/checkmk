#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, Optional

from .agent_based_api.v1 import Attributes, register, SNMPTree
from .agent_based_api.v1.type_defs import InventoryResult, StringTable
from .utils.fortinet import DETECT_FORTIGATE

Section = Mapping[str, str]

_SYSTEM_MODES = {
    "1": "standalone",
    "2": "activeActive",
    "3": "activePassive",
}
_LBSCHED_MODES = {
    "1": "none",
    "2": "hub",
    "3": "leastConnections",
    "4": "roundRobin",
    "5": "weightedRoundRobin",
    "6": "random",
    "7": "ipBased",
    "8": "ipPortBased",
}


def parse_fortigate_ha(string_table: StringTable) -> Optional[Section]:
    if not string_table:
        return None
    table_data = string_table[0]
    parsed = {
        "mode": _SYSTEM_MODES.get(table_data[0], "unknown"),
        "group_id": table_data[1],
        "prio": table_data[2],
        "sched": _LBSCHED_MODES.get(table_data[3], "unknown"),
        "group_name": table_data[4],
    }
    return parsed


register.snmp_section(
    name="fortigate_ha",
    parse_function=parse_fortigate_ha,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12356.101.13.1",
        oids=[
            "1",  # fgHaSystemMode
            "2",  # fgHaGroupId
            "3",  # fgHaPriority
            "6",  # fgHaSchedule
            "7",  # fgHaGroupName
        ],
    ),
    detect=DETECT_FORTIGATE,
)


def inventory_fortigate_ha(section: Section) -> InventoryResult:
    yield Attributes(
        path=["software", "applications", "fortinet", "fortigate_high_availability"],
        inventory_attributes={
            "Mode": section["mode"],
            "Priority": section["prio"],
            "Schedule": section["sched"],
            "Group ID": section["group_id"],
            "Group Name": section["group_name"],
        },
    )


register.inventory_plugin(
    name="fortigate_ha",
    inventory_function=inventory_fortigate_ha,
)
