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
    get_value_store,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.cpu_util import check_cpu_util


@dataclass(frozen=True)
class Section:
    max_cpu: int
    cpu: float
    uptime: int


def parse_proxmox_ve_cpu_util(string_table: StringTable) -> Section:
    data = json.loads(string_table[0][0])

    return Section(
        max_cpu=int(data["max_cpu"]),
        cpu=float(data["cpu"]),
        uptime=int(data["uptime"]),
    )


def discover_single(section: Section) -> DiscoveryResult:
    yield Service()


def check_proxmox_ve_cpu_util(params: Mapping[str, Any], section: Section) -> CheckResult:
    check_cpu_util_params = {"util": params["util"][1], "average": params["average"]}
    yield from check_cpu_util(
        util=section.cpu * 100,
        params=check_cpu_util_params,
        value_store=get_value_store(),
        this_time=section.uptime,
    )

    yield Result(state=State.OK, summary=f"CPU cores assigned: {section.max_cpu}")

    check_levels_params = params["util"]
    if params["util"][0] == "fixed":
        (warn, crit) = params["util"][1]
        check_levels_params = (
            "fixed",
            (warn * section.max_cpu / 100, crit * section.max_cpu / 100),
        )

    yield from check_levels(
        value=round(section.max_cpu * section.cpu, 2),
        levels_upper=check_levels_params,
        metric_name="cpu_core_usage",
        label="Total CPU Core usage",
        boundaries=(0.0, section.max_cpu),
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
        "util": ("fixed", (90.0, 95.0)),
        "average": 1,
    },
)
