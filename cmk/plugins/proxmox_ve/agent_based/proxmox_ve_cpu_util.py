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
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.cpu_util import check_cpu_util

Section = Mapping[str, float]


def parse_proxmox_ve_cpu_util(string_table: StringTable) -> Section:
    return {key: float(value) for key, value in json.loads(string_table[0][0]).items()}


def discover_single(section: Section) -> DiscoveryResult:
    yield Service()


def check_proxmox_ve_cpu_util(
    params: Mapping[str, Any], section: Section
) -> CheckResult:
    """
    >>> for result in check_proxmox_ve_cpu_util(
    ...     {
    ...         "util": (90.0, 95.0),
    ...     },
    ...     parse_proxmox_ve_cpu_util([['{"max_cpu": 16.0, "cpu": 0.319682438494757, "uptime": 2427306.0}']])):
    ...   print(result)
    Result(state=<State.OK: 0>, summary='Total CPU: 31.97%')
    Metric('util', 31.9682438494757, levels=(90.0, 95.0), boundaries=(0.0, 100.0))
    Result(state=<State.OK: 0>, summary='CPU cores assigned: 16')
    Result(state=<State.OK: 0>, summary='CPU Core usage: 5.11')
    Metric('cpu_core_usage', 5.11, levels=(14.4, 15.2), boundaries=(0.0, 16.0)
    """
    max_cpu = int(section.get("max_cpu", 0))
    cpu_util = float(section.get("cpu", 0))
    uptime = int(section.get("uptime", 0))

    value_store = get_value_store()

    yield from check_cpu_util(
        util=cpu_util * 100,
        params=params,
        value_store=value_store,
        this_time=uptime,
    )

    yield Result(state=State.OK, summary=f"CPU cores assigned: {max_cpu}")

    if params["util"] is not None:
        (warn, crit) = params["util"]
        cores_levels = (warn * max_cpu / 100, crit * max_cpu / 100)
    else:
        cores_levels = None

    yield from check_levels_v1(
        value=round(max_cpu * cpu_util, 2),
        levels_upper=cores_levels,
        metric_name="cpu_core_usage",
        label="CPU Core usage",
        boundaries=(0.0, max_cpu),
    )


agent_section_proxmox_ve_cpu_util = AgentSection(
    name="proxmox_ve_cpu_util",
    parse_function=parse_proxmox_ve_cpu_util,
)

check_plugin_proxmox_ve_cpu_util = CheckPlugin(
    name="proxmox_ve_cpu_util",
    service_name="Proxmox VE CPU Utilization",
    discovery_function=discover_single,
    check_function=check_proxmox_ve_cpu_util,
    check_ruleset_name="proxmox_ve_cpu_util",
    check_default_parameters={
        "util": (90.0, 95.0),
    },
)
