#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# F5OS rSeries platform CPU
# MIB: F5-PLATFORM-STATS-MIB (enterprise .1.3.6.1.4.1.12276.1)

import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TypedDict

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Metric,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.f5os_rseries.lib.detect import DETECT_F5OS_RSERIES
from cmk.plugins.lib.cpu_util import check_cpu_util


@dataclass(frozen=True)
class F5OSCPUSection:
    current: float  # cpuCurrent (%)
    avg_5sec: float  # cpuTotal5secAvg (%)
    avg_1min: float  # cpuTotal1minAvg (%)
    avg_5min: float  # cpuTotal5minAvg (%)


def parse_f5os_rseries_cpu(string_table: StringTable) -> F5OSCPUSection | None:
    if not string_table:
        return None
    row = string_table[0]
    return F5OSCPUSection(
        current=float(row[1]),  # cpuCurrent (unit: 1%)
        avg_5sec=float(row[2]),  # cpuTotal5secAvg (unit: 1%)
        avg_1min=float(row[3]),  # cpuTotal1minAvg (unit: 1%)
        avg_5min=float(row[4]),  # cpuTotal5minAvg (unit: 1%)
    )


snmp_section_f5os_rseries_cpu = SimpleSNMPSection(
    name="f5os_rseries_cpu",
    parse_function=parse_f5os_rseries_cpu,
    detect=DETECT_F5OS_RSERIES,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12276.1.2.1.1.2.1",
        oids=[
            "1",  # cpuCore (row label, not used in check)
            "2",  # cpuCurrent (unit: 1%)
            "3",  # cpuTotal5secAvg (unit: 1%)
            "4",  # cpuTotal1minAvg (unit: 1%)
            "5",  # cpuTotal5minAvg (unit: 1%)
        ],
    ),
)


def discover_f5os_rseries_cpu(section: F5OSCPUSection) -> DiscoveryResult:
    yield Service()


class _CPUParams(TypedDict, total=False):
    # The cpu_utilization ruleset delivers a bare (warn, crit) tuple (or a predictive-levels
    # mapping) under "util"; check_cpu_util interprets both, plus the optional "average".
    util: tuple[float, float] | Mapping[str, object]
    average: int


def check_f5os_rseries_cpu(params: _CPUParams, section: F5OSCPUSection) -> CheckResult:
    yield from check_cpu_util(
        util=section.avg_1min,
        params=params,
        value_store=get_value_store(),
        this_time=time.time(),
    )
    yield Result(
        state=State.OK,
        notice=(
            f"Current: {section.current:.0f}%, "
            f"5 sec avg: {section.avg_5sec:.0f}%, "
            f"5 min avg: {section.avg_5min:.0f}%"
        ),
    )
    yield Metric("util_5sec", section.avg_5sec)
    yield Metric("util_5min", section.avg_5min)


check_plugin_f5os_rseries_cpu = CheckPlugin(
    name="f5os_rseries_cpu",
    sections=["f5os_rseries_cpu"],
    service_name="F5OS Platform CPU",
    discovery_function=discover_f5os_rseries_cpu,
    check_function=check_f5os_rseries_cpu,
    check_default_parameters={"util": (80.0, 90.0)},
    check_ruleset_name="cpu_utilization",
)
