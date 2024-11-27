#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_legacy_includes.mem import check_memory_element

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import any_of, contains, SNMPTree, StringTable

check_info = {}

# FIXME
# The WATO group 'memory_simple' needs an item and the service_description should
# have a '%s'.  At the moment the current empty item '' and 'Memory' without '%s'
# works but is not consistent.  This will be fixed in the future.
# If we change this we loose history and parameter sets have to be adapted.

# Author: Lars Michelsen <lm@mathias-kettner.de>

# Relevant SNMP OIDs:
# hpLocalMemTotalBytes   1.3.6.1.4.1.11.2.14.11.5.1.1.2.1.1.1.5
# hpLocalMemFreeBytes    1.3.6.1.4.1.11.2.14.11.5.1.1.2.1.1.1.6
# hpLocalMemAllocBytes   1.3.6.1.4.1.11.2.14.11.5.1.1.2.1.1.1.7


def discover_hp_procurve_mem(info):
    if len(info) == 1 and int(info[0][0]) >= 0:
        yield None, {}


def check_hp_procurve_mem(_no_item, params, info):
    if len(info) != 1:
        return None

    if isinstance(params, tuple):
        params = {"levels": ("perc_used", params)}
    mem_total, mem_used = (int(mem) for mem in info[0])
    return check_memory_element(
        "Usage",
        mem_used,
        mem_total,
        params.get("levels"),
        metric_name="mem_used",
    )


def parse_hp_procurve_mem(string_table: StringTable) -> StringTable:
    return string_table


check_info["hp_procurve_mem"] = LegacyCheckDefinition(
    name="hp_procurve_mem",
    parse_function=parse_hp_procurve_mem,
    detect=any_of(
        contains(".1.3.6.1.2.1.1.2.0", ".11.2.3.7.11"),
        contains(".1.3.6.1.2.1.1.2.0", ".11.2.3.7.8"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11.2.14.11.5.1.1.2.1.1.1",
        oids=["5", "7"],
    ),
    service_name="Memory",
    discovery_function=discover_hp_procurve_mem,
    check_function=check_hp_procurve_mem,
    check_ruleset_name="memory_simple_single",
    check_default_parameters={"levels": ("perc_used", (80.0, 90.0))},
)
