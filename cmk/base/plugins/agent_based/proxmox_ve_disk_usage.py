#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Any, Mapping

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    Metric,
    register,
    render,
    Result,
    Service,
    State,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)

Section = Mapping[str, float]


def parse_proxmox_ve_disk_usage(string_table: StringTable) -> Section:
    return {key: float(value) for key, value in json.loads(string_table[0][0]).items()}


def discover_single(section: Section) -> DiscoveryResult:
    yield Service()


def check_proxmox_ve_disk_usage(params: Mapping[str, Any], section: Section) -> CheckResult:
    """
    >>> for result in check_proxmox_ve_disk_usage(
    ...     {"levels": (80., 90.)},
    ...     parse_proxmox_ve_disk_usage([['{"disk": 1073741824, "max_disk": 2147483648}']])):
    ...   print(result)
    Metric('fs_used', 1073741824.0, levels=(1717986918.4, 1932735283.2), boundaries=(0.0, 2147483648.0))
    Metric('fs_size', 2147483648.0, boundaries=(0.0, None))
    Metric('fs_used_percent', 50.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0))
    Result(state=<State.OK: 0>, summary='50.00% used (1.07 GB of 2.15 GB)')
    """
    used_bytes, total_bytes = section.get("disk", 0), section.get("max_disk", 0)
    warn, crit = params.get("levels", (0.0, 0.0))
    warn_bytes, crit_bytes = (warn / 100 * total_bytes, crit / 100 * total_bytes)

    if total_bytes == 0:
        yield Result(state=State.WARN, summary="Size of filesystem is 0 B")
        return

    yield Metric(
        "fs_used",
        used_bytes,
        levels=(warn_bytes, crit_bytes),
        boundaries=(0, total_bytes),
    )
    yield Metric(
        "fs_size",
        total_bytes,
        boundaries=(0, None),
    )
    yield Metric(
        "fs_used_percent",
        100.0 * used_bytes / total_bytes,
        levels=(warn, crit),
        boundaries=(0.0, 100.0),
    )

    yield Result(
        state=(
            State.CRIT
            if used_bytes >= crit_bytes
            else State.WARN
            if used_bytes >= warn_bytes
            else State.OK
        ),
        summary="%s used (%s of %s)"
        % (
            render.percent(100.0 * used_bytes / total_bytes),
            render.disksize(used_bytes),
            render.disksize(total_bytes),
        ),
    )


register.agent_section(
    name="proxmox_ve_disk_usage",
    parse_function=parse_proxmox_ve_disk_usage,
)

register.check_plugin(
    name="proxmox_ve_disk_usage",
    service_name="Proxmox VE Disk Usage",
    discovery_function=discover_single,
    check_function=check_proxmox_ve_disk_usage,
    check_ruleset_name="proxmox_ve_disk_percentage_used",
    check_default_parameters={"levels": (80.0, 90.0)},
)
