#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)

from .lib import DETECT_PEAKFLOW_SP, DETECT_PEAKFLOW_TMS, DETECT_PRAVAIL


@dataclass(frozen=True)
class Section:
    ram: int
    swap: int


def parse_arbor_memory(string_table: StringTable) -> Section | None:
    return Section(int(string_table[0][0]), int(string_table[0][1])) if string_table else None


snmp_section_arbor_memory_peakflow_sp = SimpleSNMPSection(
    name="arbor_memory_peakflow_sp",
    detect=DETECT_PEAKFLOW_SP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9694.1.4.2.1",
        oids=["7.0", "10.0"],
    ),
    parse_function=parse_arbor_memory,
    parsed_section_name="arbor_memory",
    supersedes=["mem_used"],
)

snmp_section_arbor_memory_peakflow_tms = SimpleSNMPSection(
    name="arbor_memory_peakflow_tms",
    detect=DETECT_PEAKFLOW_TMS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9694.1.5.2",
        oids=["7.0", "8.0"],
    ),
    parse_function=parse_arbor_memory,
    parsed_section_name="arbor_memory",
    supersedes=["mem_used"],
)

snmp_section_arbor_memory_peakflow_pravail = SimpleSNMPSection(
    name="arbor_memory_peakflow_pravail",
    detect=DETECT_PRAVAIL,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9694.1.6.2",
        oids=["7.0", "8.0"],
    ),
    parse_function=parse_arbor_memory,
    parsed_section_name="arbor_memory",
    supersedes=["mem_used"],
)


def discover_arbor_memory(section: Section) -> DiscoveryResult:
    yield Service()


def check_arbor_memory(params: Mapping[str, Any], section: Section) -> CheckResult:
    yield from check_levels_v1(
        section.ram,
        metric_name="mem_used_percent",
        levels_upper=params["levels_ram"][1],
        label="Used RAM",
    )
    yield from check_levels_v1(
        section.swap,
        metric_name="swap_used_percent",
        levels_upper=params["levels_swap"][1],
        label="Used Swap",
    )


check_plugin_arbor_memory = CheckPlugin(
    name="arbor_memory",
    service_name="Memory",
    discovery_function=discover_arbor_memory,
    check_function=check_arbor_memory,
    check_ruleset_name="memory_arbor",
    check_default_parameters={
        "levels_ram": ("perc_used", (80.0, 90.0)),
        "levels_swap": ("perc_used", (80.0, 90.0)),
    },
)
