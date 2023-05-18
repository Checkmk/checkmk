#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import check_levels, LegacyCheckDefinition
from cmk.base.check_legacy_includes.wmi import (
    get_levels_quadruple,
    inventory_wmi_table_instances,
    parse_wmi_table,
    wmi_calculate_raw_average,
    wmi_yield_raw_persec,
)
from cmk.base.config import check_info

# checks for is store and is clienttype
# as I understand it, these are logically related but the performance
# counters are completely separate

# source for these defaults:
# https://blogs.technet.microsoft.com/samdrey/2015/01/26/exchange-2013-performance-counters-and-their-thresholds/


def discover_msexch_isclienttype(parsed):
    return inventory_wmi_table_instances(parsed)


def check_msexch_isclienttype(item, params, parsed):
    try:
        average = wmi_calculate_raw_average(parsed[""], item, "RPCAverageLatency", 1)
    except KeyError:
        yield 3, "item not present anymore", []
    else:
        yield check_levels(
            average,
            "average_latency",
            get_levels_quadruple(params["clienttype_latency"]),
            infoname="Average latency",
            unit="ms",
        )

    yield from wmi_yield_raw_persec(
        parsed[""],
        item,
        "RPCRequests",
        infoname="RPC Requests/sec",
        perfvar="requests_per_sec",
        levels=get_levels_quadruple(params["clienttype_requests"]),
    )


check_info["msexch_isclienttype"] = LegacyCheckDefinition(
    discovery_function=discover_msexch_isclienttype,
    check_function=check_msexch_isclienttype,
    parse_function=parse_wmi_table,
    service_name="Exchange IS Client Type %s",
    check_ruleset_name="msx_info_store",
    check_default_parameters={
        # attention! those three dictionaries are tuples when returned by wato!
        "store_latency": {"upper": (40.0, 50.0)},
        "clienttype_latency": {"upper": (40.0, 50.0)},
        "clienttype_requests": {"upper": (60, 70)},
    },
)
