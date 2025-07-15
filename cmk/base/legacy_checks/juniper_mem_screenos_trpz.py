#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.mem import check_memory_element
from cmk.plugins.lib.juniper import DETECT_JUNIPER_SCREENOS, DETECT_JUNIPER_TRPZ

check_info = {}


@dataclass(frozen=True)
class Section:
    used: int
    total: int


def parse_juniper_trpz_mem(string_table: StringTable) -> Section | None:
    return (
        Section(int(string_table[0][0]) * 1024, int(string_table[0][1]) * 1024)
        if string_table
        else None
    )


def discover_juniper_mem_generic(section: Section) -> Iterator[tuple[None, dict]]:
    yield None, {}


def check_juniper_mem_generic(
    _no_item: None,
    params: Mapping[str, Any],
    section: Section,
) -> tuple[int, str, list]:
    return check_memory_element(
        label="Used",
        used=section.used,
        total=section.total,
        levels=params["levels"],
        metric_name="mem_used",
    )


check_info["juniper_trpz_mem"] = LegacyCheckDefinition(
    name="juniper_trpz_mem",
    detect=DETECT_JUNIPER_TRPZ,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.14525.4.8.1.1",
        oids=["12.1", "6"],
    ),
    service_name="Memory",
    parse_function=parse_juniper_trpz_mem,
    discovery_function=discover_juniper_mem_generic,
    check_function=check_juniper_mem_generic,
    check_ruleset_name="juniper_mem",
    check_default_parameters={
        "levels": ("perc_used", (80.0, 90.0)),
    },
)


def parse_juniper_screenos_mem(string_table):
    if not string_table:
        return None
    used = int(string_table[0][0])
    free = int(string_table[0][1])
    return Section(used, used + free)


check_info["juniper_screenos_mem"] = LegacyCheckDefinition(
    name="juniper_screenos_mem",
    detect=DETECT_JUNIPER_SCREENOS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3224.16.2",
        oids=["1.0", "2.0"],
    ),
    parse_function=parse_juniper_screenos_mem,
    service_name="Memory",
    discovery_function=discover_juniper_mem_generic,
    check_function=check_juniper_mem_generic,
    check_ruleset_name="juniper_mem",
    check_default_parameters={
        "levels": ("perc_used", (80.0, 90.0)),
    },
)
