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


def parse_proxmox_ve_network_throughput(string_table: StringTable) -> Section:
    return {key: int(value) for key, value in json.loads(string_table[0][0]).items()}


def discover_single(section: Section) -> DiscoveryResult:
    yield Service()


def check_proxmox_ve_network_throughput(
    params: Mapping[str, Any], section: Section
) -> CheckResult:
    """
    >>> for result in check_proxmox_ve_network_throughput(
    ...     {
    ...         "in_levels": None,
    ...         "out_levels": None,
    ...     },
    ...     parse_proxmox_ve_network_throughput([['{"net_in": 18999433043, "net_out": 25363852710, "uptime": 2406220}']])):
    ...   print(result)
    Result(state=<State.OK: 0>, summary='Inbound: 1.29 kB/s')
    Result(state=<State.OK: 0>, summary='Outbound: 855 B/s')
    Metric('net_in_throughput', 1285.7333333333333, levels=None, boundaries=(0.0, None))
    Metric('net_out_throughput', 855.3166666666667, levels=None, boundaries=(0.0, None))
    """
    net_in = section.get("net_in", 0)
    net_out = section.get("net_out", 0)
    uptime = section.get("uptime", 0)

    value_store = get_value_store()

    last_in = value_store.get("last_in", 0)
    last_out = value_store.get("last_out", 0)
    last_uptime = value_store.get("last_uptime", 0)

    if uptime == 0:
        in_throughput = float(net_in)
        out_throughput = float(net_out)
    elif uptime > last_uptime:
        in_throughput = (net_in - last_in) / (uptime - last_uptime)
        out_throughput = (net_out - last_out) / (uptime - last_uptime)
    else:
        in_throughput = net_in / uptime
        out_throughput = net_out / uptime

    value_store["last_in"] = net_in
    value_store["last_out"] = net_out
    value_store["last_uptime"] = uptime

    yield from check_levels_v1(
        value=in_throughput,
        levels_upper=params["in_levels"],
        metric_name="net_in_throughput",
        render_func=render.iobandwidth,
        label="Inbound",
        boundaries=(0, None),
    )

    yield from check_levels_v1(
        value=out_throughput,
        levels_upper=params["out_levels"],
        metric_name="net_out_throughput",
        render_func=render.iobandwidth,
        label="Outbound",
        boundaries=(0, None),
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
        "in_levels": None,
        "out_levels": None,
    },
)
