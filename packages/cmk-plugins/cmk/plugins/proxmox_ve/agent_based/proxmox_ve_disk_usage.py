#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)

Section = Mapping[str, float]


def parse_proxmox_ve_disk_usage(string_table: StringTable) -> Section:
    return {key: float(value) for key, value in json.loads(string_table[0][0]).items()}


def discover_single(section: Section) -> DiscoveryResult:
    yield Service()


# TODO: this is exactly the same as df, except in bytes
def check_proxmox_ve_disk_usage(params: Mapping[str, Any], section: Section) -> CheckResult:
    """
    >>> for result in check_proxmox_ve_disk_usage(
    ...     {"levels": ("fixed", (80., 90.))},
    ...     parse_proxmox_ve_disk_usage([['{"disk": 1073741824, "max_disk": 2147483648}']])):
    ...   print(result)
    Metric('fs_used', 1073741824.0, levels=(1717986918.4, 1932735283.2), boundaries=(0.0, 2147483648.0))
    Metric('fs_free', 1073741824.0, boundaries=(0.0, None))
    Result(state=<State.OK: 0>, summary='Used: 50.00%')
    Metric('fs_used_percent', 50.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0))
    Result(state=<State.OK: 0>, summary='1.07 GB of 2.15 GB')
    Metric('fs_size', 2147483648.0, boundaries=(0.0, None))
    """
    used_bytes, total_bytes = section.get("disk", 0), section.get("max_disk", 0)

    if total_bytes == 0:
        yield Result(state=State.WARN, summary="Size of filesystem is 0 B")
        return

    if params["levels"][0] == "no_levels":
        yield Metric(
            "fs_used",
            used_bytes,
            boundaries=(0, total_bytes),
        )
    elif params["levels"][0] == "fixed":
        warn, crit = params["levels"][1]
        yield Metric(
            "fs_used",
            used_bytes,
            levels=(warn / 100 * total_bytes, crit / 100 * total_bytes),
            boundaries=(0, total_bytes),
        )

    yield Metric(
        "fs_free",
        total_bytes - used_bytes,
        boundaries=(0, None),
    )

    yield from check_levels(
        100.0 * used_bytes / total_bytes,
        levels_upper=params["levels"],
        metric_name="fs_used_percent",
        render_func=render.percent,
        boundaries=(0.0, 100.0),
        label="Used",
    )
    yield Result(
        state=State.OK, summary=f"{render.disksize(used_bytes)} of {render.disksize(total_bytes)}"
    )

    yield Metric(
        "fs_size",
        total_bytes,
        boundaries=(0, None),
    )


agent_section_proxmox_ve_disk_usage = AgentSection(
    name="proxmox_ve_disk_usage",
    parse_function=parse_proxmox_ve_disk_usage,
)

check_plugin_proxmox_ve_disk_usage = CheckPlugin(
    name="proxmox_ve_disk_usage",
    service_name="Proxmox VE Disk Usage",
    discovery_function=discover_single,
    check_function=check_proxmox_ve_disk_usage,
    check_ruleset_name="proxmox_ve_disk_percentage_used",
    check_default_parameters={"levels": ("fixed", (80.0, 90.0))},
)
