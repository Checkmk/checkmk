#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"


from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import get_rate, get_value_store, IgnoreResultsError, render, StringTable

check_info = {}


def discover_win_cpuusage(info):
    for line in info:
        try:
            if line[0] == "238:6":
                return [(None, {})]
        except Exception:
            pass
    return []


def check_win_cpuusage(item, params, info):
    if isinstance(params, tuple):
        levels: tuple | None = params
    elif isinstance(params, dict):
        levels = params.get("levels")
    else:  # legacy: old params may be None
        levels = None

    for line in info:
        if line[0] == "238:6":
            this_time = int(float(line[1]))
            # Windows sends one counter for each CPU plus one counter that
            # I've forgotton what's it for (idle?)
            num_cpus = len(line) - 4
            overall_perc = 0.0
            for cpu in range(0, num_cpus):
                ticks = int(line[2 + cpu])
                ticks_per_sec = get_rate(
                    get_value_store(), "cpuusage.%d" % cpu, this_time, ticks, raise_overflow=True
                )
                secs_per_sec = ticks_per_sec / 10000000.0
                used_perc = 100 * (1 - secs_per_sec)
                overall_perc += used_perc

            used_perc = overall_perc / num_cpus
            if used_perc < 0:
                used_perc = 0
            elif used_perc > 100:
                used_perc = 100

            if num_cpus == 1:
                num_txt = ""
            else:
                num_txt = " / %d CPUs" % num_cpus

            return check_levels(
                used_perc,
                "cpuusage",
                levels,
                human_readable_func=render.percent,
                infoname="Used%s" % num_txt,
                boundaries=(0, 100),
            )

    return (3, "counter for cpu (238:6) not found")


def discover_win_diskstat(info):
    for line in info:
        try:
            if line[0] == "2:16" or line[0] == "2:18":
                return [(None, None)]
        except Exception:
            pass
    return []


def check_win_diskstat(item, params, info):
    read_bytes_ctr = 0
    write_bytes_ctr = 0
    this_time = None
    for line in info:
        if line[0] == "2:16":
            read_bytes_ctr = int(line[2])
        elif line[0] == "2:18":
            write_bytes_ctr = int(line[2])
            this_time = int(float(line[1]))
            break

    if not this_time:
        return None

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

    perfdata = [("read", "%dc" % read_bytes_ctr), ("write", "%dc" % write_bytes_ctr)]
    return (
        0,
        f"reading {read_per_sec / 1024.0**2:.1f} MB/s, writing {write_per_sec / 1024.0**2:.1f} MB/s",
        perfdata,
    )


def parse_winperf(string_table: StringTable) -> StringTable:
    return string_table


check_info["winperf"] = LegacyCheckDefinition(
    name="winperf",
    parse_function=parse_winperf,
)


check_info["winperf.cpuusage"] = LegacyCheckDefinition(
    name="winperf_cpuusage",
    service_name="CPU Usage",
    sections=["winperf"],
    discovery_function=discover_win_cpuusage,
    check_function=check_win_cpuusage,
)

check_info["winperf.diskstat"] = LegacyCheckDefinition(
    name="winperf_diskstat",
    service_name="Disk IO",
    sections=["winperf"],
    discovery_function=discover_win_diskstat,
    check_function=check_win_diskstat,
)
