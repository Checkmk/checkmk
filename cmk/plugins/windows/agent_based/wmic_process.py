#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    Metric,
    Result,
    State,
    StringTable,
)


def parse_wmic_process(string_table: StringTable) -> StringTable:
    return string_table


def discover_wmic_process(section: StringTable) -> DiscoveryResult:
    # wmic_process is only available as an enforced/manual service.
    yield from ()


def check_wmic_process(
    item: str,
    params: Mapping[str, Any],
    section: StringTable,
) -> CheckResult:
    if not section:
        return
    legend, *lines = section

    # The corresponding WATO ruleset still uses a positional tuple, but that does
    # not work in the backend, so this whole function is unreachable.
    # CMK-35057: decide on whether to fix the rule or remove the check entirely.
    #
    # **If** we decide to fix it, this is what the parameters should look like.
    # adding this here to be able to migrate and keep all linters happy.
    match params:
        case {
            "name": str(name),
            "mem_levels": ("fixed", (float(memwarn), float(memcrit))),
            "page_levels": ("fixed", (float(pagewarn), float(pagecrit))),
            "cpu_levels": ("fixed", (float(cpuwarn), float(cpucrit))),
        }:
            pass
        case _:
            raise TypeError(params)

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

    mem_mb = mem / 1048576.0
    page_mb = page / 1048576.0
    user_per_sec = get_rate(
        value_store, f"wmic_process.user.{name}.{count}", now, userc, raise_overflow=True
    )
    kernel_per_sec = get_rate(
        value_store, f"wmic_process.kernel.{name}.{count}", now, kernelc, raise_overflow=True
    )
    user_perc = (user_per_sec / 100000.0) / cpucores
    kernel_perc = (kernel_per_sec / 100000.0) / cpucores
    cpu_perc = user_perc + kernel_perc

    messages = [f"{count} processes"]
    state = State.OK

    msg = f"{user_perc:.0f}%/{kernel_perc:.0f}% User/Kernel"
    if cpu_perc >= cpucrit:
        state = State.CRIT
        msg += f"(!!) (critical at {cpucrit:.0f}%)"
    elif cpu_perc >= cpuwarn:
        state = State.WARN
        msg += f"(!) (warning at {cpuwarn:.0f}%)"
    messages.append(msg)

    msg = f"{mem_mb:.1f}MB RAM"
    if 0 < memcrit <= mem_mb:
        state = State.CRIT
        msg += f"(!!) (critical at {memcrit} MB)"
    elif 0 < memwarn <= mem_mb:
        state = State.worst(state, State.WARN)
        msg += f"(!) (warning at {memwarn} MB)"
    messages.append(msg)

    msg = f"{page_mb:.0f}MB Page"
    if page_mb >= pagecrit:
        state = State.CRIT
        msg += f"(!!) (critical at {pagecrit} MB)"
    elif page_mb >= pagewarn:
        state = State.worst(state, State.WARN)
        msg += f"(!) (warning at {pagewarn} MB)"
    messages.append(msg)

    yield Result(state=state, summary=", ".join(messages))
    yield Metric("mem", mem_mb, levels=(memwarn, memcrit))
    yield Metric("page", page_mb, levels=(pagewarn, pagecrit))
    yield Metric("user", user_perc, levels=(cpuwarn, cpucrit), boundaries=(0, 100))
    yield Metric("kernel", kernel_perc, levels=(cpuwarn, cpucrit), boundaries=(0, 100))


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
    check_default_parameters={
        "name": "",
        "mem_levels": ("fixed", (0.0, 0.0)),
        "page_levels": ("fixed", (0.0, 0.0)),
        "cpu_levels": ("fixed", (0.0, 0.0)),
    },
)
