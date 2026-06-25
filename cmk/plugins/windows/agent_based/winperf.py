#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    IgnoreResultsError,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)


def parse_winperf(string_table: StringTable) -> StringTable:
    return string_table


def discover_win_cpuusage(section: StringTable) -> DiscoveryResult:
    for line in section:
        try:
            if line[0] == "238:6":
                yield Service()
                return
        except Exception:
            pass


def check_win_cpuusage(section: StringTable) -> CheckResult:
    for line in section:
        if line[0] == "238:6":
            this_time = int(float(line[1]))
            # Windows sends one counter for each CPU plus one counter that
            # I've forgotton what's it for (idle?)
            num_cpus = len(line) - 4
            overall_perc = 0.0
            for cpu in range(num_cpus):
                ticks = int(line[2 + cpu])
                ticks_per_sec = get_rate(
                    get_value_store(), f"cpuusage.{cpu}", this_time, ticks, raise_overflow=True
                )
                secs_per_sec = ticks_per_sec / 10000000.0
                used_perc = 100 * (1 - secs_per_sec)
                overall_perc += used_perc

            used_perc = overall_perc / num_cpus
            if used_perc < 0:
                used_perc = 0
            elif used_perc > 100:
                used_perc = 100

            num_txt = "" if num_cpus == 1 else f" / {num_cpus} CPUs"

            yield from check_levels_v1(
                used_perc,
                metric_name="cpuusage",
                render_func=render.percent,
                label=f"Used{num_txt}",
                boundaries=(0, 100),
            )
            return

    yield Result(state=State.UNKNOWN, summary="counter for cpu (238:6) not found")


def discover_win_diskstat(section: StringTable) -> DiscoveryResult:
    for line in section:
        try:
            if line[0] == "2:16" or line[0] == "2:18":
                yield Service()
                return
        except Exception:
            pass


def check_win_diskstat(section: StringTable) -> CheckResult:
    read_bytes_ctr = 0
    write_bytes_ctr = 0
    this_time = None
    for line in section:
        if line[0] == "2:16":
            read_bytes_ctr = int(line[2])
        elif line[0] == "2:18":
            write_bytes_ctr = int(line[2])
            this_time = int(float(line[1]))
            break

    if not this_time:
        return

    try:
        read_per_sec = get_rate(
            get_value_store(), "diskstat.read", this_time, read_bytes_ctr, raise_overflow=True
        )
        write_per_sec = get_rate(
            get_value_store(), "diskstat.write", this_time, write_bytes_ctr, raise_overflow=True
        )
    except IgnoreResultsError as e:
        # make sure that inital check does not need three cycles for all counters
        # to be initialized
        get_rate(
            get_value_store(), "diskstat.write", this_time, write_bytes_ctr, raise_overflow=True
        )
        raise e

    yield Result(
        state=State.OK,
        summary=f"reading {read_per_sec / 1024.0**2:.1f} MB/s, writing {write_per_sec / 1024.0**2:.1f} MB/s",
    )
    yield Metric("read", read_bytes_ctr)
    yield Metric("write", write_bytes_ctr)


agent_section_winperf = AgentSection(
    name="winperf",
    parse_function=parse_winperf,
)


check_plugin_winperf_cpuusage = CheckPlugin(
    name="winperf_cpuusage",
    service_name="CPU Usage",
    sections=["winperf"],
    discovery_function=discover_win_cpuusage,
    check_function=check_win_cpuusage,
)


check_plugin_winperf_diskstat = CheckPlugin(
    name="winperf_diskstat",
    service_name="Disk IO",
    sections=["winperf"],
    discovery_function=discover_win_diskstat,
    check_function=check_win_diskstat,
)
