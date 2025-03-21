#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    LevelsT,
    render,
)
from cmk.plugins.windows.agent_based.libwmi import (
    check_wmi_raw_counter,
    check_wmi_raw_persec,
    discover_wmi_table_total,
    parse_wmi_table,
    WMISection,
)

# source for these defaults:
# https://blogs.technet.microsoft.com/samdrey/2015/01/26/exchange-2013-performance-counters-and-their-thresholds/


def discover_msexch_rpcclientaccess(section: WMISection) -> DiscoveryResult:
    yield from discover_wmi_table_total(section)


class Params(TypedDict):
    latency_s: LevelsT[float]
    requests: LevelsT[int]


def check_msexch_rpcclientaccess(params: Params, section: WMISection) -> CheckResult:
    # despite the source being raw-data, the averaged latency is
    # pre-processed

    table = section[""]
    try:
        latency = table.get(0, "RPCAveragedLatency")
        if latency is None:
            return
    except KeyError:
        return

    yield from check_levels(
        float(latency) / 1000.0,
        label="Average latency",
        metric_name="average_latency_s",
        levels_upper=params["latency_s"],
        render_func=render.timespan,
    )
    yield from check_wmi_raw_persec(
        table,
        "",
        "RPCRequests",
        label="RPC Requests/sec",
        metric_name="requests_per_sec",
        levels_upper=params["requests"],
    )
    yield from check_wmi_raw_counter(
        table, "", "UserCount", label="Users", metric_name="current_users"
    )
    yield from check_wmi_raw_counter(
        table, "", "ActiveUserCount", label="Active users", metric_name="active_users"
    )


agent_section_msexch_rpcclientaccess = AgentSection(
    name="msexch_rpcclientaccess",
    parse_function=parse_wmi_table,
)

check_plugin_msexch_rpcclientaccess = CheckPlugin(
    name="msexch_rpcclientaccess",
    service_name="Exchange RPC Client Access",
    discovery_function=discover_msexch_rpcclientaccess,
    check_function=check_msexch_rpcclientaccess,
    check_ruleset_name="msx_rpcclientaccess",
    check_default_parameters=Params(
        latency_s=("fixed", (0.2, 0.25)),
        requests=("fixed", (30, 40)),
    ),
)
