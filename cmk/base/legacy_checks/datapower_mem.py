#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_legacy_includes.mem import check_memory_element

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.datapower import DETECT

check_info = {}


def inventory_datapower_mem(info):
    if info:
        yield None, {}


def check_datapower_mem(item, params, info):
    mem_total_bytes = int(info[0][0]) * 1024
    mem_used_bytes = int(info[0][1]) * 1024

    return check_memory_element(
        "Usage",
        mem_used_bytes,
        mem_total_bytes,
        params.get("levels"),
        metric_name="mem_used",
    )


def parse_datapower_mem(string_table: StringTable) -> StringTable:
    return string_table


check_info["datapower_mem"] = LegacyCheckDefinition(
    name="datapower_mem",
    parse_function=parse_datapower_mem,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.14685.3.1.5",
        oids=["2", "3"],
    ),
    service_name="Memory",
    discovery_function=inventory_datapower_mem,
    check_function=check_datapower_mem,
    check_ruleset_name="memory_simple_single",
    check_default_parameters={"levels": ("perc_used", (80.0, 90.0))},
)
