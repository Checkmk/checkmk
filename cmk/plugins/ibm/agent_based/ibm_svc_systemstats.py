#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections import defaultdict
from collections.abc import Mapping
from typing import Any, NamedTuple

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.cpu_util import check_cpu_util

Item = str
StatName = str

VDISK_STATS = ["vdisk_r_mb", "vdisk_w_mb", "vdisk_r_io", "vdisk_w_io", "vdisk_r_ms", "vdisk_w_ms"]
MDISK_STATS = ["mdisk_r_mb", "mdisk_w_mb", "mdisk_r_io", "mdisk_w_io", "mdisk_r_ms", "mdisk_w_ms"]
DRIVE_STATS = ["drive_r_mb", "drive_w_mb", "drive_r_io", "drive_w_io", "drive_r_ms", "drive_w_ms"]


class IBMSystemStats(NamedTuple):
    cpu_pc: int | None = None
    total_cache_pc: int | None = None
    write_cache_pc: int | None = None
    disks: Mapping[Item, Mapping[StatName, float]] = {}


def ibm_svc_systemstats_parse(string_table: StringTable) -> IBMSystemStats:
    cpu_pc = None
    total_cache_pc = None
    write_cache_pc = None
    disks: dict[Item, dict[StatName, float]] = defaultdict(dict)

    for stat_name, stat_current, _stat_peak, _stat_peak_time in string_table:
        if stat_name == "cpu_pc":
            cpu_pc = int(stat_current)

        elif stat_name == "total_cache_pc":
            total_cache_pc = int(stat_current)

        elif stat_name == "write_cache_pc":
            write_cache_pc = int(stat_current)

        if stat_name in VDISK_STATS:
            short_stat_name = stat_name.replace("vdisk_", "")
            disks["VDisks"][short_stat_name] = float(stat_current)

        elif stat_name in MDISK_STATS:
            short_stat_name = stat_name.replace("mdisk_", "")
            disks["MDisks"][short_stat_name] = float(stat_current)

        elif stat_name in DRIVE_STATS:
            short_stat_name = stat_name.replace("drive_", "")
            disks["Drives"][short_stat_name] = float(stat_current)

    return IBMSystemStats(
        cpu_pc=cpu_pc, total_cache_pc=total_cache_pc, write_cache_pc=write_cache_pc, disks=disks
    )


agent_section_ibm_svc_systemstats = AgentSection(
    name="ibm_svc_systemstats",
    parse_function=ibm_svc_systemstats_parse,
)


def discovery_ibm_svc_systemstats_disks(section: IBMSystemStats) -> DiscoveryResult:
    for item in section.disks:
        yield Service(item=item)


#   .--disk IO-------------------------------------------------------------.
#   |                         _ _     _      ___ ___                       |
#   |                      __| (_)___| | __ |_ _/ _ \                      |
#   |                     / _` | / __| |/ /  | | | | |                     |
#   |                    | (_| | \__ \   <   | | |_| |                     |
#   |                     \__,_|_|___/_|\_\ |___\___/                      |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_ibm_svc_systemstats_diskio(item: str, section: IBMSystemStats) -> CheckResult:
    if item not in section.disks:
        return

    read_bytes = section.disks[item]["r_mb"] * 1024 * 1024
    write_bytes = section.disks[item]["w_mb"] * 1024 * 1024

    yield Result(
        state=State.OK,
        summary=f"{render.iobandwidth(read_bytes)} read, {render.iobandwidth(write_bytes)} write",
    )
    yield Metric("read", read_bytes)
    yield Metric("write", write_bytes)


check_plugin_ibm_svc_systemstats_diskio = CheckPlugin(
    name="ibm_svc_systemstats_diskio",
    sections=["ibm_svc_systemstats"],
    service_name="Throughput %s Total",
    discovery_function=discovery_ibm_svc_systemstats_disks,
    check_function=check_ibm_svc_systemstats_diskio,
)

# .
#   .--iops----------------------------------------------------------------.
#   |                          _                                           |
#   |                         (_) ___  _ __  ___                           |
#   |                         | |/ _ \| '_ \/ __|                          |
#   |                         | | (_) | |_) \__ \                          |
#   |                         |_|\___/| .__/|___/                          |
#   |                                 |_|                                  |
#   '----------------------------------------------------------------------'


def check_ibm_svc_systemstats_iops(item: str, section: IBMSystemStats) -> CheckResult:
    if item not in section.disks:
        return

    read_iops = section.disks[item]["r_io"]
    write_iops = section.disks[item]["w_io"]

    yield Result(state=State.OK, summary=f"{read_iops} IO/s read, {write_iops} IO/s write")
    yield Metric("read", read_iops)
    yield Metric("write", write_iops)


check_plugin_ibm_svc_systemstats_iops = CheckPlugin(
    name="ibm_svc_systemstats_iops",
    sections=["ibm_svc_systemstats"],
    service_name="IOPS %s Total",
    discovery_function=discovery_ibm_svc_systemstats_disks,
    check_function=check_ibm_svc_systemstats_iops,
)


# .
#   .--disk latency--------------------------------------------------------.
#   |             _ _     _      _       _                                 |
#   |          __| (_)___| | __ | | __ _| |_ ___ _ __   ___ _   _          |
#   |         / _` | / __| |/ / | |/ _` | __/ _ \ '_ \ / __| | | |         |
#   |        | (_| | \__ \   <  | | (_| | ||  __/ | | | (__| |_| |         |
#   |         \__,_|_|___/_|\_\ |_|\__,_|\__\___|_| |_|\___|\__, |         |
#   |                                                       |___/          |
#   '----------------------------------------------------------------------'


def check_ibm_svc_systemstats_disk_latency(
    item: str, params: Mapping[str, Any], section: IBMSystemStats
) -> CheckResult:
    if item not in section.disks:
        return

    for name, value in [
        ("read", section.disks[item]["r_ms"]),
        ("write", section.disks[item]["w_ms"]),
    ]:
        yield from check_levels_v1(
            value=value,
            metric_name=f"{name}_latency",
            levels_upper=params.get(name),
            label=f"{name} latency",
            render_func=lambda x: f"{x} ms",
        )


check_plugin_ibm_svc_systemstats_disk_latency = CheckPlugin(
    name="ibm_svc_systemstats_disk_latency",
    sections=["ibm_svc_systemstats"],
    service_name="Latency %s Total",
    discovery_function=discovery_ibm_svc_systemstats_disks,
    check_function=check_ibm_svc_systemstats_disk_latency,
    check_ruleset_name="ibm_svc_total_latency",
    check_default_parameters={},
)

# .
#   .--cpu-----------------------------------------------------------------.
#   |                                                                      |
#   |                           ___ _ __  _   _                            |
#   |                          / __| '_ \| | | |                           |
#   |                         | (__| |_) | |_| |                           |
#   |                          \___| .__/ \__,_|                           |
#   |                              |_|                                     |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discovery_ibm_svc_systemstats_cpu(section: IBMSystemStats) -> DiscoveryResult:
    if section.cpu_pc is not None:
        yield Service()


def check_ibm_svc_systemstats_cpu(
    params: Mapping[str, tuple[float, float]], section: IBMSystemStats
) -> CheckResult:
    if section.cpu_pc is not None:
        yield from check_cpu_util(
            util=section.cpu_pc,
            params=params,
            perf_max=100.0,
            value_store=get_value_store(),
            this_time=time.time(),
        )
        return

    yield Result(state=State.UNKNOWN, summary="value cpu_pc not found in agent output")


check_plugin_ibm_svc_systemstats_cpu_util = CheckPlugin(
    name="ibm_svc_systemstats_cpu_util",
    sections=["ibm_svc_systemstats"],
    service_name="CPU utilization Total",
    discovery_function=discovery_ibm_svc_systemstats_cpu,
    check_function=check_ibm_svc_systemstats_cpu,
    check_ruleset_name="cpu_utilization",
    check_default_parameters={"util": (90.0, 95.0)},
)


# .
#   .--cache---------------------------------------------------------------.
#   |                                     _                                |
#   |                       ___ __ _  ___| |__   ___                       |
#   |                      / __/ _` |/ __| '_ \ / _ \                      |
#   |                     | (_| (_| | (__| | | |  __/                      |
#   |                      \___\__,_|\___|_| |_|\___|                      |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discovery_ibm_svc_systemstats_cache(section: IBMSystemStats) -> DiscoveryResult:
    if section.total_cache_pc is not None:
        yield Service()


def check_ibm_svc_systemstats_cache(section: IBMSystemStats) -> CheckResult:
    write_cache_pc = section.write_cache_pc
    total_cache_pc = section.total_cache_pc

    if total_cache_pc is None:
        yield Result(state=State.UNKNOWN, summary="value total_cache_pc not found in agent output")
        return
    if write_cache_pc is None:
        yield Result(state=State.UNKNOWN, summary="value write_cache_pc not found in agent output")
        return

    yield Result(
        state=State.OK,
        summary=f"Write cache usage is {write_cache_pc} %, total cache usage is {total_cache_pc} %",
    )
    yield Metric("write_cache_pc", write_cache_pc, boundaries=(0, 100))
    yield Metric("total_cache_pc", total_cache_pc, boundaries=(0, 100))


check_plugin_ibm_svc_systemstats_cache = CheckPlugin(
    name="ibm_svc_systemstats_cache",
    sections=["ibm_svc_systemstats"],
    service_name="Cache Total",
    discovery_function=discovery_ibm_svc_systemstats_cache,
    check_function=check_ibm_svc_systemstats_cache,
)
