#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    LevelsT,
    render,
)
from cmk.plugins.windows.agent_based.libwmi import (
    check_wmi_raw_average,
    check_wmi_raw_persec,
    discover_wmi_table_instances,
    parse_wmi_table,
    WMISection,
)

# checks for is store and is clienttype
# as I understand it, these are logically related but the performance
# counters are completely separate

# source for these defaults:
# https://blogs.technet.microsoft.com/samdrey/2015/01/26/exchange-2013-performance-counters-and-their-thresholds/


def discover_msexch_isclienttype(section: WMISection) -> DiscoveryResult:
    yield from discover_wmi_table_instances(section)


class Params(TypedDict):
    store_latency_s: LevelsT[float]
    clienttype_latency_s: LevelsT[float]
    clienttype_requests: LevelsT[int]


def check_msexch_isclienttype(item: str, params: Params, section: WMISection) -> CheckResult:
    table = section[""]
    yield from check_wmi_raw_average(
        table,
        item,
        "RPCAverageLatency",
        0.001,
        metric_name="average_latency_s",
        levels_upper=params["clienttype_latency_s"],
        label="Average latency",
        render_func=render.timespan,
    )

    yield from check_wmi_raw_persec(
        table,
        item,
        "RPCRequests",
        metric_name="requests_per_sec",
        levels_upper=params["clienttype_requests"],
        label="RPC Requests/sec",
    )


agent_section_msexch_isclienttype = AgentSection(
    name="msexch_isclienttype",
    parse_function=parse_wmi_table,
)

check_plugin_msexch_isclienttype = CheckPlugin(
    name="msexch_isclienttype",
    service_name="Exchange IS Client Type %s",
    discovery_function=discover_msexch_isclienttype,
    check_function=check_msexch_isclienttype,
    check_ruleset_name="msx_info_store",
    check_default_parameters=Params(
        store_latency_s=("fixed", (0.04, 0.05)),
        clienttype_latency_s=("fixed", (0.04, 0.05)),
        clienttype_requests=("fixed", (60, 70)),
    ),
)
