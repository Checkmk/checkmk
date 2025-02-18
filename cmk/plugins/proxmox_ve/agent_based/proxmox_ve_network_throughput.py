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
    Result,
    Service,
    State,
    StringTable,
)

Section = Mapping[str, int]


def parse_proxmox_ve_network_throughput(string_table: StringTable) -> Section:
    return {key: int(value) for key, value in json.loads(string_table[0][0]).items()}


def discover_single(section: Section) -> DiscoveryResult:
    yield Service()


def check_proxmox_ve_network_throughput(params: Mapping[str, Any], section: Section) -> CheckResult:
    net_in = section.get("net_in", 0)
    net_out = section.get("net_out", 0)
    uptime = section.get("uptime", 0)

    try:
        value_store = get_value_store()

        last_in = value_store.get("last_in", 0)
        last_out = value_store.get("last_out", 0)
        last_uptime = value_store.get("last_uptime", 0)

        if uptime == 0:
            in_throughput: float = net_in
            out_throughput: float = net_out
        elif uptime > last_uptime:
            in_throughput = (net_in - last_in) / (uptime - last_uptime)
            out_throughput = (net_out - last_out) / (uptime - last_uptime)
        else:
            in_throughput = net_in / uptime
            out_throughput = net_out / uptime

        value_store["last_in"] = net_in
        value_store["last_out"] = net_out
        value_store["last_uptime"] = uptime

        in_levels = params["in_levels"]
        out_levels = params["out_levels"]
        if in_levels is not None:
            in_levels = (in_levels[0] * 1024**2, in_levels[1] * 1024**2)
        if out_levels is not None:
            out_levels = (out_levels[0] * 1024**2, out_levels[1] * 1024**2)

        yield from check_levels_v1(
            value=in_throughput,
            levels_upper=in_levels,
            metric_name="net_in_throughput",
            render_func=render.iobandwidth,
            label="Inbound",
            boundaries=(0, None),
        )

        yield from check_levels_v1(
            value=out_throughput,
            levels_upper=out_levels,
            metric_name="net_out_throughput",
            render_func=render.iobandwidth,
            label="Outbound",
            boundaries=(0, None),
        )
    except AssertionError:
        yield Result(state=State.UNKNOWN, summary="error checking datastore status")


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
