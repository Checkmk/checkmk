#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.v1 import GetRateError
from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    IgnoreResults,
    render,
    Service,
    StringTable,
)


@dataclass(frozen=True)
class Section:
    net_in: int
    net_out: int
    uptime: int


def parse_proxmox_ve_network_throughput(string_table: StringTable) -> Section:
    data = json.loads(string_table[0][0])
    return Section(
        net_in=int(data["net_in"]),
        net_out=int(data["net_out"]),
        uptime=int(data["uptime"]),
    )


def discover_single(section: Section) -> DiscoveryResult:
    yield Service()


def check_proxmox_ve_network_throughput(params: Mapping[str, Any], section: Section) -> CheckResult:
    now = float(section.uptime)

    net_in = section.net_in
    try:
        net_in_rate = get_rate(get_value_store(), "net_in", now, net_in, raise_overflow=True)
    except GetRateError as e:
        yield IgnoreResults(str(e))
    else:
        yield from check_levels(
            net_in_rate,
            label="Inbound",
            metric_name="net_in_throughput",
            levels_upper=params["in_levels"],
            render_func=render.iobandwidth,
        )

    net_out = section.net_out
    try:
        net_out_rate = get_rate(get_value_store(), "net_out", now, net_out, raise_overflow=True)
    except GetRateError as e:
        yield IgnoreResults(str(e))
    else:
        yield from check_levels(
            net_out_rate,
            label="Outbound",
            metric_name="net_out_throughput",
            levels_upper=params["out_levels"],
            render_func=render.iobandwidth,
        )


agent_section_proxmox_ve_network_throughput = AgentSection(
    name="proxmox_ve_network_throughput",
    parse_function=parse_proxmox_ve_network_throughput,
)

check_plugin_proxmox_ve_network_throughput = CheckPlugin(
    name="proxmox_ve_network_throughput",
    service_name="Proxmox VE Network Throughput",
    discovery_function=discover_single,
    check_function=check_proxmox_ve_network_throughput,
    check_ruleset_name="proxmox_ve_network_throughput",
    check_default_parameters={
        "in_levels": ("no_levels", None),
        "out_levels": ("no_levels", None),
    },
)
