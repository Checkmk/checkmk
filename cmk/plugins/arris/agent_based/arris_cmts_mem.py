#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any, Literal

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    equals,
    OIDEnd,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.memory import check_element

Section = Mapping[str, Mapping[str, float]]


def parse_arris_cmts_mem(string_table: StringTable) -> Section:
    parsed: dict[str, Mapping[str, float]] = {}
    for cid, heap, heap_free in string_table:
        # The Module numbers are starting with 0, not with 1 like the OIDs
        heap_f, heap_free_f = float(heap), float(heap_free)
        parsed.setdefault(
            str(int(cid) - 1),
            {
                "mem_used": heap_f - heap_free_f,
                "mem_total": heap_f,
            },
        )
    return parsed


def discover_arris_cmts_mem(section: Section) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_arris_cmts_mem(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return
    levels = params.get("levels")
    if not isinstance(levels, tuple):
        memory_levels = None
    else:
        mode: Literal["abs_used", "perc_used"] = (
            "abs_used" if isinstance(levels[0], int) else "perc_used"
        )
        memory_levels = (mode, levels)
    yield from check_element(
        "Usage",
        data["mem_used"],
        data["mem_total"],
        memory_levels,
        metric_name="mem_used",
    )


snmp_section_arris_cmts_mem = SimpleSNMPSection(
    name="arris_cmts_mem",
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.4998.2.1"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.4998.1.1.5.3.2.1.1",
        oids=[OIDEnd(), "2", "3"],
    ),
    parse_function=parse_arris_cmts_mem,
)


check_plugin_arris_cmts_mem = CheckPlugin(
    name="arris_cmts_mem",
    service_name="Memory Module %s",
    discovery_function=discover_arris_cmts_mem,
    check_function=check_arris_cmts_mem,
    check_ruleset_name="memory_multiitem",
    check_default_parameters={
        "levels": (80.0, 90.0),
    },
)
