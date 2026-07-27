#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# F5OS rSeries platform memory
# MIB: F5-PLATFORM-STATS-MIB (enterprise .1.3.6.1.4.1.12276.1)

from dataclasses import dataclass
from typing import TypedDict

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    render,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.f5os_rseries.lib.detect import DETECT_F5OS_RSERIES


@dataclass(frozen=True)
class F5OSMemorySection:
    mem_used: int  # platformMemUsed (bytes)
    mem_free: int  # platformMemFree (bytes)
    mem_used_percent: float  # platformMemUsedPercent (%)
    mem_total: int  # platformMemTotal (bytes)
    mem_avail: int  # platformMemAvail (bytes)


def parse_f5os_rseries_memory(string_table: StringTable) -> F5OSMemorySection | None:
    if not string_table:
        return None
    row = string_table[0]
    return F5OSMemorySection(
        mem_used=int(row[0]),  # platformMemUsed (unit: 1 byte)
        mem_free=int(row[1]),  # platformMemFree (unit: 1 byte)
        mem_used_percent=float(row[2]),  # platformMemUsedPercent (unit: 1%)
        mem_total=int(row[3]),  # platformMemTotal (unit: 1 byte)
        mem_avail=int(row[4]),  # platformMemAvail (unit: 1 byte)
    )


snmp_section_f5os_rseries_memory = SimpleSNMPSection(
    name="f5os_rseries_memory",
    parse_function=parse_f5os_rseries_memory,
    detect=DETECT_F5OS_RSERIES,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12276.1.2.1.4.1.1",
        oids=[
            "2",  # platformMemUsed (unit: 1 byte)
            "3",  # platformMemFree (unit: 1 byte)
            "4",  # platformMemUsedPercent (unit: 1%)
            "5",  # platformMemTotal (unit: 1 byte)
            "6",  # platformMemAvail (unit: 1 byte)
        ],
    ),
)


def discover_f5os_rseries_memory(section: F5OSMemorySection) -> DiscoveryResult:
    yield Service()


class _MemoryParams(TypedDict):
    # The 2.4 memory_percentage_used ruleset (SimpleLevels) delivers a bare (warn, crit)
    # percentage tuple, or None for "no levels".
    levels: tuple[float, float] | None


def check_f5os_rseries_memory(params: _MemoryParams, section: F5OSMemorySection) -> CheckResult:
    levels = params["levels"]
    yield from check_levels(
        section.mem_used_percent,
        label="Used",
        metric_name="mem_used_percent",
        render_func=render.percent,
        levels_upper=("fixed", levels) if levels else ("no_levels", None),
    )
    yield Result(
        state=State.OK,
        notice=(
            f"Used: {render.bytes(section.mem_used)}, "
            f"Total: {render.bytes(section.mem_total)}, "
            f"Available: {render.bytes(section.mem_avail)}"
        ),
    )
    yield Metric("mem_used", float(section.mem_used))
    yield Metric("mem_total", float(section.mem_total))


check_plugin_f5os_rseries_memory = CheckPlugin(
    name="f5os_rseries_memory",
    sections=["f5os_rseries_memory"],
    service_name="F5OS Platform Memory",
    discovery_function=discover_f5os_rseries_memory,
    check_function=check_f5os_rseries_memory,
    check_default_parameters={"levels": (80.0, 90.0)},
    check_ruleset_name="memory_percentage_used",
)
