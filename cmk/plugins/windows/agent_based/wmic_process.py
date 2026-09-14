#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from typing import NotRequired, TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    FixedLevelsT,
    get_rate,
    get_value_store,
    Metric,
    NoLevelsT,
    render,
    Result,
    State,
    StringTable,
)

# WMI reports CPU times in 100ns ticks, so a fully busy core accumulates 10^7 ticks
# per second. Dividing the tick rate by a hundredth of that yields percent of one core;
# the check divides by the core count afterwards to get percent of the whole host.
_TICK_RATE_PER_PERCENT = 100000.0

_BYTES_PER_MB = 1048576.0

# The ruleset only offers fixed levels, so predictive levels cannot occur here.
type _Levels = NoLevelsT | FixedLevelsT[float]


class Params(TypedDict):
    name: NotRequired[str]
    mem_levels: _Levels
    page_levels: _Levels
    cpu_levels: _Levels


def parse_wmic_process(string_table: StringTable) -> StringTable:
    return string_table


def discover_wmic_process(section: StringTable) -> DiscoveryResult:  # noqa: ARG001
    # wmic_process is only available as an enforced/manual service.
    yield from ()


def _fixed_levels(levels: _Levels) -> tuple[float, float] | None:
    """Reduce the levels to the plain warn/crit pair `Metric` understands."""
    match levels:
        case ("fixed", (warn, crit)):
            return warn, crit
        case ("no_levels", None):
            return None
        case other:
            # (sk): The type says this cannot happen, but the parameters come from disk.
            raise TypeError(f"Unexpected level parameters: {other!r}")


def _render_mb(value: float) -> str:
    return f"{value:.1f} MB"


def check_wmic_process(
    item: str,  # noqa: ARG001
    params: Params,
    section: StringTable,
) -> CheckResult:
    if not (name := params.get("name")):
        yield Result(state=State.UNKNOWN, summary="No process name configured")
        return

    if not section:
        # Without a result the engine reports "Item not found in monitoring data", which
        # blames the item instead of the agent plug-in that produced nothing.
        yield Result(state=State.UNKNOWN, summary="No output from agent in section wmic_process")
        return
    legend, *lines = section

    count, mem, page, userc, kernelc = 0, 0, 0, 0, 0
    cpucores = 1

    value_store = get_value_store()
    now = time.time()

    for line in lines:
        psinfo = dict(zip(legend, line))
        if psinfo.get("Name") is None:
            continue
        if "ThreadCount" in legend and psinfo["Name"].lower() == "system idle process":
            cpucores = int(psinfo["ThreadCount"])
        elif psinfo["Name"].lower() == name.lower():
            count += 1
            mem += int(psinfo["WorkingSetSize"])
            page += int(psinfo["PageFileUsage"])
            userc += int(psinfo["UserModeTime"])
            kernelc += int(psinfo["KernelModeTime"])

    mem_mb = mem / _BYTES_PER_MB
    page_mb = page / _BYTES_PER_MB
    # The counters are a sum over a set of processes that comes and goes, so the sum is
    # not monotonic. Keying on the count, as the legacy check did, restarts the rate
    # whenever the set changes instead of reporting the jump as a rate.
    user_per_sec = get_rate(
        value_store, f"wmic_process.user.{name}.{count}", now, userc, raise_overflow=True
    )
    kernel_per_sec = get_rate(
        value_store, f"wmic_process.kernel.{name}.{count}", now, kernelc, raise_overflow=True
    )
    user_perc = (user_per_sec / _TICK_RATE_PER_PERCENT) / cpucores
    kernel_perc = (kernel_per_sec / _TICK_RATE_PER_PERCENT) / cpucores
    cpu_perc = user_perc + kernel_perc

    yield Result(state=State.OK, summary=f"Processes: {count}")

    yield from check_levels(
        cpu_perc,
        levels_upper=params["cpu_levels"],
        render_func=render.percent,
        label="CPU",
    )
    cpu_levels = _fixed_levels(params["cpu_levels"])
    yield Metric("user", user_perc, levels=cpu_levels, boundaries=(0, 100))
    yield Metric("kernel", kernel_perc, levels=cpu_levels, boundaries=(0, 100))

    yield from check_levels(
        mem_mb,
        levels_upper=params["mem_levels"],
        metric_name="mem",
        render_func=_render_mb,
        label="RAM",
    )
    yield from check_levels(
        page_mb,
        levels_upper=params["page_levels"],
        metric_name="page",
        render_func=_render_mb,
        label="Page file",
    )


agent_section_wmic_process = AgentSection(
    name="wmic_process",
    parse_function=parse_wmic_process,
)


check_plugin_wmic_process = CheckPlugin(
    name="wmic_process",
    service_name="Process %s",
    discovery_function=discover_wmic_process,
    check_function=check_wmic_process,
    check_ruleset_name="wmic_process",
    check_default_parameters=Params(
        mem_levels=("no_levels", None),
        page_levels=("no_levels", None),
        cpu_levels=("no_levels", None),
    ),
)
