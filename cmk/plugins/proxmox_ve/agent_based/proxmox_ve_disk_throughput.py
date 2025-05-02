#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    GetRateError,
    IgnoreResults,
    render,
    Service,
    StringTable,
)


@dataclass(frozen=True)
class Section:
    disk_read: int
    disk_write: int
    uptime: int


def parse_proxmox_ve_disk_throughput(string_table: StringTable) -> Section:
    data = json.loads(string_table[0][0])
    return Section(
        disk_read=int(data["disk_read"]),
        disk_write=int(data["disk_write"]),
        uptime=int(data["uptime"]),
    )


def discover_single(section: Section) -> DiscoveryResult:
    yield Service()


def check_proxmox_ve_disk_throughput(params: Mapping[str, Any], section: Section) -> CheckResult:
    now = float(section.uptime)

    disk_read = section.disk_read
    try:
        disk_read_rate = get_rate(
            get_value_store(), "disk_read", now, disk_read, raise_overflow=True
        )
    except GetRateError as e:
        yield IgnoreResults(str(e))
    else:
        yield from check_levels(
            disk_read_rate,
            label="Disk read",
            metric_name="disk_read_throughput",
            levels_upper=params["read_levels"],
            render_func=render.iobandwidth,
        )

    disk_write = section.disk_write
    try:
        disk_write_rate = get_rate(
            get_value_store(), "disk_write", now, disk_write, raise_overflow=True
        )
    except GetRateError as e:
        yield IgnoreResults(str(e))
    else:
        yield from check_levels(
            disk_write_rate,
            label="Disk write",
            metric_name="disk_write_throughput",
            levels_upper=params["write_levels"],
            render_func=render.iobandwidth,
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
        "read_levels": ("no_levels", None),
        "write_levels": ("no_levels", None),
    },
)
