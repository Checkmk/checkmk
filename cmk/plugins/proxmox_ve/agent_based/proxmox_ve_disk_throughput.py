#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    render,
    Service,
    StringTable,
)

Section = Mapping[str, int]


def parse_proxmox_ve_disk_throughput(string_table: StringTable) -> Section:
    return {key: int(value) for key, value in json.loads(string_table[0][0]).items()}


def discover_single(section: Section) -> DiscoveryResult:
    yield Service()


def check_proxmox_ve_disk_throughput(
    params: Mapping[str, Any], section: Section
) -> CheckResult:
    """
    >>> for result in check_proxmox_ve_disk_throughput(
    ...     {
    ...         "read_levels": None,
    ...         "write_levels": None,
    ...     },
    ...     parse_proxmox_ve_disk_throughput([['{"disk_read": 234944108544, "disk_write": 5909099398656, "uptime": 2343655}']])):
    ...   print(result)
    Result(state=<State.OK: 0>, summary='Read IO: 8.53 B/s')
    Result(state=<State.OK: 0>, summary='Write IO: 2.90 MB/s')
    Metric('disk_read_throughput', 2184.533333333333, levels=None, boundaries=(0.0, None))
    Metric('disk_write_throughput', 2738558.780952381, levels=None, boundaries=(0.0, None))
    """
    disk_read = section.get("disk_read", 0)
    disk_write = section.get("disk_write", 0)
    uptime = section.get("uptime", 0)

    value_store = get_value_store()

    last_read = value_store.get("last_read", 0)
    last_write = value_store.get("last_write", 0)
    last_uptime = value_store.get("last_uptime", 0)

    if uptime == 0:
        read_throughput = float(disk_read)
        write_throughput = float(disk_write)
    elif uptime > last_uptime:
        read_throughput = (disk_read - last_read) / (uptime - last_uptime)
        write_throughput = (disk_write - last_write) / (uptime - last_uptime)
    else:
        read_throughput = disk_read / uptime
        write_throughput = disk_write / uptime

    value_store["last_read"] = disk_read
    value_store["last_write"] = disk_write
    value_store["last_uptime"] = uptime

    yield from check_levels_v1(
        value=read_throughput,
        levels_upper=params["read_levels"],
        metric_name="disk_read_throughput",
        render_func=render.iobandwidth,
        label="Read",
        boundaries=(0, None),
    )

    yield from check_levels_v1(
        value=write_throughput,
        levels_upper=params["write_levels"],
        metric_name="disk_write_throughput",
        render_func=render.iobandwidth,
        label="Write",
        boundaries=(0, None),
    )


agent_section_proxmox_ve_disk_throughput = AgentSection(
    name="proxmox_ve_disk_throughput",
    parse_function=parse_proxmox_ve_disk_throughput,
)

check_plugin_proxmox_ve_disk_throughput = CheckPlugin(
    name="proxmox_ve_disk_throughput",
    service_name="Proxmox VE Disk Throughput",
    discovery_function=discover_single,
    check_function=check_proxmox_ve_disk_throughput,
    check_ruleset_name="proxmox_ve_disk_throughput",
    check_default_parameters={
        "read_levels": None,
        "write_levels": None,
    },
)
