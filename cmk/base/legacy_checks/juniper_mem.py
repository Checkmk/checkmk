#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from collections.abc import Iterable, Mapping

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import render, SNMPTree, StringTable
from cmk.plugins.juniper.lib import DETECT_JUNIPER

check_info = {}

# .1.3.6.1.4.1.2636.3.1.13.1.5.9.1.0.0 Routing Engine 0 --> JUNIPER-MIB::jnxOperatingDescr.9.1.0.0
# .1.3.6.1.4.1.2636.3.1.13.1.5.9.2.0.0 Routing Engine 1 --> JUNIPER-MIB::jnxOperatingDescr.9.2.0.0
# .1.3.6.1.4.1.2636.3.1.13.1.11.9.1.0.0 37 --> JUNIPER-MIB::jnxOperatingBuffer.9.1.0.0
# .1.3.6.1.4.1.2636.3.1.13.1.11.9.2.0.0 36 --> JUNIPER-MIB::jnxOperatingBuffer.9.2.0.0


Section = Mapping[str, float]

DiscoveryResult = Iterable[tuple[str, Mapping]]
CheckResult = Iterable[tuple[int, str, list]]


def parse_juniper_mem(string_table: StringTable) -> Section:
    return {k: float(v) for k, v in string_table}


def discover_juniper_mem(section: Section) -> DiscoveryResult:
    yield from ((k, {}) for k in section)


def check_juniper_mem(
    item: str, params: Mapping[str, tuple[float, float]], section: Section
) -> CheckResult:
    if (memory_percent := section.get(item)) is None:
        return

    yield check_levels(
        memory_percent,
        "mem_used_percent",
        params["levels"],
        human_readable_func=render.percent,
        infoname="Used",
    )


check_info["juniper_mem"] = LegacyCheckDefinition(
    name="juniper_mem",
    detect=DETECT_JUNIPER,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2636.3.1.13.1",
        oids=["5.9", "11.9"],
    ),
    parse_function=parse_juniper_mem,
    service_name="Memory %s",
    discovery_function=discover_juniper_mem,
    check_function=check_juniper_mem,
    check_ruleset_name="juniper_mem_modules",
    check_default_parameters={
        "levels": (80.0, 90.0),
    },
)
