#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    LevelsT,
    render,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.juniper.lib import DETECT_JUNIPER

# .1.3.6.1.4.1.2636.3.1.13.1.5.9.1.0.0 Routing Engine 0 --> JUNIPER-MIB::jnxOperatingDescr.9.1.0.0
# .1.3.6.1.4.1.2636.3.1.13.1.5.9.2.0.0 Routing Engine 1 --> JUNIPER-MIB::jnxOperatingDescr.9.2.0.0
# .1.3.6.1.4.1.2636.3.1.13.1.11.9.1.0.0 37 --> JUNIPER-MIB::jnxOperatingBuffer.9.1.0.0
# .1.3.6.1.4.1.2636.3.1.13.1.11.9.2.0.0 36 --> JUNIPER-MIB::jnxOperatingBuffer.9.2.0.0


Section = Mapping[str, float]


def parse_juniper_mem(string_table: StringTable) -> Section:
    return {k: float(v) for k, v in string_table}


def discover_juniper_mem(section: Section) -> DiscoveryResult:
    for k in section:
        yield Service(item=k)


def _migrate_levels(levels: object) -> LevelsT[float] | None:
    # Legacy rules stored bare tuples (warn, crit); v2 API requires tagged tuples.
    # TODO (mr) migrate juniper_mem_modules.py.
    if isinstance(levels, tuple) and len(levels) == 2 and isinstance(levels[0], float):
        return ("fixed", levels)
    return levels  # type: ignore[return-value]


def check_juniper_mem(item: str, params: Mapping[str, object], section: Section) -> CheckResult:
    if (memory_percent := section.get(item)) is None:
        return

    yield from check_levels(
        memory_percent,
        metric_name="mem_used_percent",
        levels_upper=_migrate_levels(params.get("levels")),
        render_func=render.percent,
        label="Used",
    )


snmp_section_juniper_mem = SimpleSNMPSection(
    name="juniper_mem",
    detect=DETECT_JUNIPER,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2636.3.1.13.1",
        oids=["5.9", "11.9"],
    ),
    parse_function=parse_juniper_mem,
)

check_plugin_juniper_mem = CheckPlugin(
    name="juniper_mem",
    service_name="Memory %s",
    discovery_function=discover_juniper_mem,
    check_function=check_juniper_mem,
    check_ruleset_name="juniper_mem_modules",
    check_default_parameters={
        "levels": (80.0, 90.0),
    },
)
