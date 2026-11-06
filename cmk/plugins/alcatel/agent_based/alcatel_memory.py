#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import TypedDict

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    LevelsT,
    render,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.agent_based.v3_unstable import discover_one_service
from cmk.plugins.alcatel.lib import DETECT_ALCATEL, DETECT_ALCATEL_AOS7


class Params(TypedDict):
    levels: LevelsT[float]


def parse_alcatel_memory(string_table: StringTable) -> float | None:
    return float(string_table[0][0]) if string_table else None


def check_alcatel_memory(params: Params, section: float) -> CheckResult:
    yield from check_levels(
        section,
        metric_name="mem_used_percent",
        levels_upper=params["levels"],
        label="Usage",
        render_func=render.percent,
    )


snmp_section_alcatel_memory = SimpleSNMPSection(
    name="alcatel_memory",
    detect=DETECT_ALCATEL,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.6486.800.1.2.1.16.1.1.1",
        oids=["9"],  # healthDeviceMemoryLatest
    ),
    parse_function=parse_alcatel_memory,
    supersedes=["hr_mem"],
)
snmp_section_alcatel_memory_aos7 = SimpleSNMPSection(
    name="alcatel_memory_aos7",
    parsed_section_name="alcatel_memory",
    detect=DETECT_ALCATEL_AOS7,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.6486.801.1.2.1.16.1.1.1.1.1",
        oids=["16"],  # healthModuleMemoryLatest
    ),
    parse_function=parse_alcatel_memory,
    supersedes=["hr_mem"],
)
check_plugin_alcatel_memory = CheckPlugin(
    name="alcatel_memory",
    service_name="Memory",
    discovery_function=discover_one_service,
    check_function=check_alcatel_memory,
    check_ruleset_name="memory_percentage_used",
    check_default_parameters=Params(levels=("fixed", (80.0, 90.0))),
)
