#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.mem import check_memory_element
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree
from cmk.agent_based.v2.type_defs import StringTable
from cmk.plugins.lib.datapower import DETECT

# FIXME
# The WATO group 'memory_simple' needs an item and the service_description should
# have a '%s'.  At the moment the current empty item '' and 'Memory' without '%s'
# works but is not consistent.  This will be fixed in the future.
# If we change this we loose history and parameter sets have to be adapted.


def inventory_datapower_mem(info):
    # TODO: Cleanup empty string and change manpage
    if info:
        return [("", {})]
    return []


def check_datapower_mem(item, params, info):
    mem_total_bytes = int(info[0][0]) * 1024
    mem_used_bytes = int(info[0][1]) * 1024

    return check_memory_element(
        "Usage", mem_used_bytes, mem_total_bytes, params.get("levels"), metric_name="mem_used"
    )


def parse_datapower_mem(string_table: StringTable) -> StringTable:
    return string_table


check_info["datapower_mem"] = LegacyCheckDefinition(
    parse_function=parse_datapower_mem,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.14685.3.1.5",
        oids=["2", "3"],
    ),
    service_name="Memory",
    discovery_function=inventory_datapower_mem,
    check_function=check_datapower_mem,
    check_ruleset_name="memory_simple",
    check_default_parameters={"levels": ("perc_used", (80.0, 90.0))},
)
