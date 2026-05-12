#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    any_of,
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.memory import check_element

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


def parse_hp_procurve_mem(string_table: StringTable) -> StringTable:
    return string_table


def discover_hp_procurve_mem(section: StringTable) -> DiscoveryResult:
    if len(section) == 1 and int(section[0][0]) >= 0:
        yield Service()


def check_hp_procurve_mem(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    if len(section) != 1:
        return

    levels = params.get("levels")
    if isinstance(levels, tuple) and len(levels) == 2 and not isinstance(levels[0], str):
        # legacy params: a plain (warn, crit) tuple
        levels = ("perc_used", levels)

    mem_total, mem_used = (int(mem) for mem in section[0])
    yield from check_element(
        "Usage",
        mem_used,
        mem_total,
        levels,
        metric_name="mem_used",
    )


snmp_section_hp_procurve_mem = SimpleSNMPSection(
    name="hp_procurve_mem",
    detect=any_of(
        contains(".1.3.6.1.2.1.1.2.0", ".11.2.3.7.11"),
        contains(".1.3.6.1.2.1.1.2.0", ".11.2.3.7.8"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11.2.14.11.5.1.1.2.1.1.1",
        oids=["5", "7"],
    ),
    parse_function=parse_hp_procurve_mem,
)


check_plugin_hp_procurve_mem = CheckPlugin(
    name="hp_procurve_mem",
    service_name="Memory",
    discovery_function=discover_hp_procurve_mem,
    check_function=check_hp_procurve_mem,
    check_ruleset_name="memory_simple_single",
    check_default_parameters={"levels": ("perc_used", (80.0, 90.0))},
)
