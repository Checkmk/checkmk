#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import render, SNMPTree, StringTable
from cmk.plugins.lib.tplink import DETECT_TPLINK

check_info = {}


def inventory_tplink_mem(info):
    if len(info) >= 1:
        return [(None, {})]
    return []


def check_tplink_mem(_no_item, params, info):
    num_units = 0
    mem_used = 0.0
    for line in info:
        unit_used = int(line[0])
        mem_used += unit_used
        num_units += 1

    if num_units == 0:
        return None

    mem_used = float(mem_used) / num_units

    return check_levels(
        mem_used,
        "mem_used_percent",
        params.get("levels", (None, None)),
        infoname="Usage",
        human_readable_func=render.percent,
    )


def parse_tplink_mem(string_table: StringTable) -> StringTable:
    return string_table


check_info["tplink_mem"] = LegacyCheckDefinition(
    name="tplink_mem",
    parse_function=parse_tplink_mem,
    detect=DETECT_TPLINK,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11863.6.4.1.2.1.1",
        oids=["2"],
    ),
    service_name="Memory",
    discovery_function=inventory_tplink_mem,
    check_function=check_tplink_mem,
    check_ruleset_name="memory_percentage_used",
    check_default_parameters={"levels": None},
)
