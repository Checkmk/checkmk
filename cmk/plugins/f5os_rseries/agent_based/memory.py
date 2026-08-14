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
    LevelsT,
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
    # Column semantics per F5-PLATFORM-STATS-MIB memoryStatsTable
    # (.1.3.6.1.4.1.12276.1.2.1.4.1.1). Note memPercentageUsed is the overall figure
    # (counts tenant reservations); the platform used/total pair is the appliance's own.
    available: int  # memAvailable (bytes)
    free: int  # memFree (bytes)
    percentage_used: float  # memPercentageUsed - overall, incl. tenant reservations (%)
    platform_total: int  # memPlatformTotal (bytes)
    platform_used: int  # memPlatformUsed (bytes)


def parse_f5os_rseries_memory(string_table: StringTable) -> F5OSMemorySection | None:
    if not string_table:
        return None
    row = string_table[0]
    return F5OSMemorySection(
        available=int(row[0]),  # memAvailable (unit: 1 byte)
        free=int(row[1]),  # memFree (unit: 1 byte)
        percentage_used=float(row[2]),  # memPercentageUsed (unit: 1%)
        platform_total=int(row[3]),  # memPlatformTotal (unit: 1 byte)
        platform_used=int(row[4]),  # memPlatformUsed (unit: 1 byte)
    )


snmp_section_f5os_rseries_memory = SimpleSNMPSection(
    name="f5os_rseries_memory",
    parse_function=parse_f5os_rseries_memory,
    detect=DETECT_F5OS_RSERIES,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12276.1.2.1.4.1.1",
        oids=[
            "2",  # memAvailable (unit: 1 byte)
            "3",  # memFree (unit: 1 byte)
            "4",  # memPercentageUsed - overall, incl. tenant reservations (unit: 1%)
            "5",  # memPlatformTotal (unit: 1 byte)
            "6",  # memPlatformUsed (unit: 1 byte)
        ],
    ),
)


def discover_f5os_rseries_memory(section: F5OSMemorySection) -> DiscoveryResult:
    yield Service()


class _MemoryParams(TypedDict):
    levels: LevelsT[float]


def check_f5os_rseries_memory(params: _MemoryParams, section: F5OSMemorySection) -> CheckResult:
    # Alert on the platform's own memory usage. The MIB's overall memPercentageUsed counts
    # tenant memory reservations and OS overhead, so it sits permanently high (~93 %) and is
    # a poor health signal; memPlatformUsed / memPlatformTotal reflects the appliance itself.
    platform_used_percent = (
        100.0 * section.platform_used / section.platform_total if section.platform_total else 0.0
    )
    yield from check_levels(
        platform_used_percent,
        label="Platform used",
        metric_name="mem_used_percent",
        render_func=render.percent,
        levels_upper=params["levels"],
    )
    yield Result(
        state=State.OK,
        notice=(
            f"Platform used: {render.bytes(section.platform_used)} of "
            f"{render.bytes(section.platform_total)}; "
            f"Available: {render.bytes(section.available)}; "
            f"Overall used incl. tenant reservations: {render.percent(section.percentage_used)}"
        ),
    )
    yield Metric("mem_used", float(section.platform_used))
    yield Metric("mem_total", float(section.platform_total))


check_plugin_f5os_rseries_memory = CheckPlugin(
    name="f5os_rseries_memory",
    sections=["f5os_rseries_memory"],
    service_name="F5OS Platform Memory",
    discovery_function=discover_f5os_rseries_memory,
    check_function=check_f5os_rseries_memory,
    check_default_parameters={"levels": ("fixed", (80.0, 90.0))},
    check_ruleset_name="memory_percentage_used",
)
