#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="arg-type"

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.wmi import (
    inventory_wmi_table_total,
    parse_wmi_table,
    wmi_yield_raw_counter,
    wmi_yield_raw_persec,
)
from cmk.base.config import check_info

# source for these defaults:
# https://blogs.technet.microsoft.com/samdrey/2015/01/26/exchange-2013-performance-counters-and-their-thresholds/


def discover_msexch_rpcclientaccess(parsed):
    return inventory_wmi_table_total(parsed)


def check_msexch_rpcclientaccess(_no_item, params, parsed):
    # despite the source being raw-data, the averaged latency is
    # pre-processed
    table = parsed[""]
    yield from wmi_yield_raw_counter(
        table,
        None,
        "RPCAveragedLatency",
        infoname="Average latency",
        perfvar="average_latency",
        levels=params["latency"],
        unit="ms",
    )
    yield from wmi_yield_raw_persec(
        table,
        None,
        "RPCRequests",
        infoname="RPC Requests/sec",
        perfvar="requests_per_sec",
        levels=params["requests"],
    )
    yield from wmi_yield_raw_counter(
        table, None, "UserCount", infoname="Users", perfvar="current_users"
    )
    yield from wmi_yield_raw_counter(
        table, None, "ActiveUserCount", infoname="Active users", perfvar="active_users"
    )


check_info["msexch_rpcclientaccess"] = LegacyCheckDefinition(
    parse_function=parse_wmi_table,
    service_name="Exchange RPC Client Access",
    discovery_function=discover_msexch_rpcclientaccess,
    check_function=check_msexch_rpcclientaccess,
    check_ruleset_name="msx_rpcclientaccess",
    check_default_parameters={
        "latency": (200.0, 250.0),
        "requests": (30, 40),
    },
)
