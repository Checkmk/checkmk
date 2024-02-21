#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.mem import check_memory_element
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.checkpoint import DETECT

# comNET GmbH, Fabian Binder

# .1.3.6.1.4.1.2620.1.6.7.4.3.0 8101654528 --> CHECKPOINT-MIB::memTotalReal
# .1.3.6.1.4.1.2620.1.6.7.4.4.0 2091094016 --> CHECKPOINT-MIB::memAvailReal


def inventory_checkpoint_memory(info):
    if info and len(info[0]) > 1:
        yield None, {}


def check_checkpoint_memory(item, params, info):
    if isinstance(params, tuple):
        params = {"levels": ("perc_used", params)}

    mem_total_bytes, mem_used_bytes = map(int, info[0])
    return check_memory_element(
        "Usage",
        mem_used_bytes,
        mem_total_bytes,
        params.get("levels"),
        metric_name="memory_used",
    )


def parse_checkpoint_memory(string_table: StringTable) -> StringTable:
    return string_table


check_info["checkpoint_memory"] = LegacyCheckDefinition(
    parse_function=parse_checkpoint_memory,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2620.1.6.7.4",
        oids=["3", "4"],
    ),
    service_name="Memory System",
    discovery_function=inventory_checkpoint_memory,
    check_function=check_checkpoint_memory,
    check_ruleset_name="memory_simple_single",
    check_default_parameters={"levels": ("perc_used", (80.0, 90.0))},
)
