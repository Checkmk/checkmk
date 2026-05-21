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
    get_value_store,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.ibm.lib_svc import parse_ibm_svc_with_header
from cmk.plugins.lib.cpu_util import check_cpu_util

Section = Mapping[str, Mapping[str, float]]

# newer Firmware versions may return decimal values, not just integer
# <<<ibm_svc_nodestats:sep(58)>>>
# node_id:node_name:stat_name:stat_current:stat_peak:stat_peak_time
# 6:BLUBBSVC01:compression_cpu_pc:0:0:230119164649
# 6:BLUBBSVC01:cpu_pc:16:18:230119164614
# 6:BLUBBSVC01:fc_mb:572:598:230119164619
# 6:BLUBBSVC01:fc_io:48940:75775:230119164614
# 6:BLUBBSVC01:sas_mb:0:0:230119164649
# 6:BLUBBSVC01:sas_io:0:0:230119164649
# 6:BLUBBSVC01:iscsi_mb:0:0:230119164649
# 6:BLUBBSVC01:iscsi_io:0:0:230119164649
# 6:BLUBBSVC01:write_cache_pc:34:34:230119164649
# 6:BLUBBSVC01:total_cache_pc:79:80:230119164444
# 6:BLUBBSVC01:vdisk_mb:391:394:230119164619
# 6:BLUBBSVC01:vdisk_io:23885:25737:230119164619
# 6:BLUBBSVC01:vdisk_ms:0.216:0.278:230119164229
# 6:BLUBBSVC01:mdisk_mb:172:220:230119164154
# 6:BLUBBSVC01:mdisk_io:9832:9832:230119164649
# 6:BLUBBSVC01:mdisk_ms:0.324:0.440:230119164634
# 6:BLUBBSVC01:drive_mb:0:0:230119164649
# 6:BLUBBSVC01:drive_io:0:0:230119164649
# 6:BLUBBSVC01:drive_ms:0.000:0.000:230119164649
# 6:BLUBBSVC01:vdisk_r_mb:388:388:230119164649
# 6:BLUBBSVC01:vdisk_r_io:23401:24944:230119164619
# 6:BLUBBSVC01:vdisk_r_ms:0.217:0.280:230119164229
# 6:BLUBBSVC01:vdisk_w_mb:2:27:230119164539
# 6:BLUBBSVC01:vdisk_w_io:482:2660:230119164334
# 6:BLUBBSVC01:vdisk_w_ms:0.191:0.455:230119164309
# 6:BLUBBSVC01:mdisk_r_mb:168:194:230119164154
# 6:BLUBBSVC01:mdisk_r_io:9700:9700:230119164649
# 6:BLUBBSVC01:mdisk_r_ms:0.323:0.453:230119164634
# 6:BLUBBSVC01:mdisk_w_mb:3:51:230119164334
# 6:BLUBBSVC01:mdisk_w_io:132:1715:230119164334
# 6:BLUBBSVC01:mdisk_w_ms:0.393:0.446:230119164204
# 6:BLUBBSVC01:drive_r_mb:0:0:230119164649
# 6:BLUBBSVC01:drive_r_io:0:0:230119164649
# 6:BLUBBSVC01:drive_r_ms:0.000:0.000:230119164649
# 6:BLUBBSVC01:drive_w_mb:0:0:230119164649
# 6:BLUBBSVC01:drive_w_io:0:0:230119164649
# 6:BLUBBSVC01:drive_w_ms:0.000:0.000:230119164649


def parse_ibm_svc_nodestats(string_table: StringTable) -> Section:
    dflt_header = [
        "node_id",
        "node_name",
        "stat_name",
        "stat_current",
        "stat_peak",
        "stat_peak_time",
    ]
    parsed: dict[str, dict[str, float]] = {}
    for rows in parse_ibm_svc_with_header(string_table, dflt_header).values():
        for data in rows:
            node_name = data["node_name"]
            stat_name = data["stat_name"]
            if stat_name in (
                "vdisk_r_mb",
                "vdisk_w_mb",
                "vdisk_r_io",
                "vdisk_w_io",
                "vdisk_r_ms",
                "vdisk_w_ms",
            ):
                item_name = f"VDisks {node_name}"
                stat_name = stat_name.replace("vdisk_", "")
            elif stat_name in (
                "mdisk_r_mb",
                "mdisk_w_mb",
                "mdisk_r_io",
                "mdisk_w_io",
                "mdisk_r_ms",
                "mdisk_w_ms",
            ):
                item_name = f"MDisks {node_name}"
                stat_name = stat_name.replace("mdisk_", "")
            elif stat_name in (
                "drive_r_mb",
                "drive_w_mb",
                "drive_r_io",
                "drive_w_io",
                "drive_r_ms",
                "drive_w_ms",
            ):
                item_name = f"Drives {node_name}"
                stat_name = stat_name.replace("drive_", "")
            elif stat_name in ("write_cache_pc", "total_cache_pc", "cpu_pc"):
                item_name = node_name
            else:
                continue
            try:
                stat_current = float(data["stat_current"])
            except ValueError:
                continue
            parsed.setdefault(item_name, {}).setdefault(stat_name, stat_current)
    return parsed


agent_section_ibm_svc_nodestats = AgentSection(
    name="ibm_svc_nodestats",
    parse_function=parse_ibm_svc_nodestats,
)


#   .--disk IO-------------------------------------------------------------.
#   |                         _ _     _      ___ ___                       |
#   |                      __| (_)___| | __ |_ _/ _ \                      |
#   |                     / _` | / __| |/ /  | | | | |                     |
#   |                    | (_| | \__ \   <   | | |_| |                     |
#   |                     \__,_|_|___/_|\_\ |___\___/                      |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_ibm_svc_nodestats_diskio(section: Section) -> DiscoveryResult:
    yield from (
        Service(item=node_name)
        for node_name, data in section.items()
        if "r_mb" in data and "w_mb" in data
    )


def check_ibm_svc_nodestats_diskio(item: str, section: Section) -> CheckResult:
    if (data := section.get(item)) is None:
        return

    read_bytes = data["r_mb"] * 1024 * 1024
    write_bytes = data["w_mb"] * 1024 * 1024

    yield Result(
        state=State.OK,
        summary=f"{render.iobandwidth(read_bytes)} read, {render.iobandwidth(write_bytes)} write",
    )
    yield Metric("read", read_bytes)
    yield Metric("write", write_bytes)


check_plugin_ibm_svc_nodestats_diskio = CheckPlugin(
    name="ibm_svc_nodestats_diskio",
    service_name="Disk IO %s",
    sections=["ibm_svc_nodestats"],
    discovery_function=discover_ibm_svc_nodestats_diskio,
    check_function=check_ibm_svc_nodestats_diskio,
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


def discover_ibm_svc_nodestats_iops(section: Section) -> DiscoveryResult:
    yield from (
        Service(item=node_name)
        for node_name, data in section.items()
        if "r_io" in data and "w_io" in data
    )


def check_ibm_svc_nodestats_iops(item: str, section: Section) -> CheckResult:
    if (data := section.get(item)) is None:
        return

    read_iops = data["r_io"]
    write_iops = data["w_io"]

    yield Result(state=State.OK, summary=f"{read_iops} IO/s read, {write_iops} IO/s write")
    yield Metric("read", read_iops)
    yield Metric("write", write_iops)


check_plugin_ibm_svc_nodestats_iops = CheckPlugin(
    name="ibm_svc_nodestats_iops",
    service_name="Disk IOPS %s",
    sections=["ibm_svc_nodestats"],
    discovery_function=discover_ibm_svc_nodestats_iops,
    check_function=check_ibm_svc_nodestats_iops,
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


def discover_ibm_svc_nodestats_disk_latency(section: Section) -> DiscoveryResult:
    yield from (
        Service(item=node_name)
        for node_name, data in section.items()
        if "r_ms" in data and "w_ms" in data
    )


def check_ibm_svc_nodestats_disk_latency(item: str, section: Section) -> CheckResult:
    if (data := section.get(item)) is None:
        return

    read_latency = data["r_ms"]
    write_latency = data["w_ms"]

    yield Result(
        state=State.OK,
        summary=f"Latency is {read_latency} ms for read, {write_latency} ms for write",
    )
    yield Metric("read_latency", read_latency)
    yield Metric("write_latency", write_latency)


check_plugin_ibm_svc_nodestats_disk_latency = CheckPlugin(
    name="ibm_svc_nodestats_disk_latency",
    service_name="Disk Latency %s",
    sections=["ibm_svc_nodestats"],
    discovery_function=discover_ibm_svc_nodestats_disk_latency,
    check_function=check_ibm_svc_nodestats_disk_latency,
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


def discover_ibm_svc_nodestats_cpu(section: Section) -> DiscoveryResult:
    yield from (Service(item=node_name) for node_name, data in section.items() if "cpu_pc" in data)


def check_ibm_svc_nodestats_cpu(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if (data := section.get(item)) is None:
        return
    yield from check_cpu_util(
        util=data["cpu_pc"],
        params=params,
        value_store=get_value_store(),
        this_time=time.time(),
    )


check_plugin_ibm_svc_nodestats_cpu_util = CheckPlugin(
    name="ibm_svc_nodestats_cpu_util",
    service_name="CPU utilization %s",
    sections=["ibm_svc_nodestats"],
    discovery_function=discover_ibm_svc_nodestats_cpu,
    check_function=check_ibm_svc_nodestats_cpu,
    check_ruleset_name="cpu_utilization_multiitem",
    check_default_parameters={"levels": (90.0, 95.0)},
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


def discover_ibm_svc_nodestats_cache(section: Section) -> DiscoveryResult:
    yield from (
        Service(item=node_name)
        for node_name, data in section.items()
        if "write_cache_pc" in data and "total_cache_pc" in data
    )


def check_ibm_svc_nodestats_cache(item: str, section: Section) -> CheckResult:
    if (data := section.get(item)) is None:
        return

    write_cache_pc = data["write_cache_pc"]
    total_cache_pc = data["total_cache_pc"]

    yield Result(
        state=State.OK,
        summary=(
            f"Write cache usage is {int(write_cache_pc)} %, "
            f"total cache usage is {int(total_cache_pc)} %"
        ),
    )
    yield Metric("write_cache_pc", write_cache_pc, boundaries=(0, 100))
    yield Metric("total_cache_pc", total_cache_pc, boundaries=(0, 100))


check_plugin_ibm_svc_nodestats_cache = CheckPlugin(
    name="ibm_svc_nodestats_cache",
    service_name="Cache %s",
    sections=["ibm_svc_nodestats"],
    discovery_function=discover_ibm_svc_nodestats_cache,
    check_function=check_ibm_svc_nodestats_cache,
)
