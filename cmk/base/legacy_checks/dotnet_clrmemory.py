#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_legacy_includes.wmi import (
    inventory_wmi_table_instances,
    wmi_filter_global_only,
    wmi_yield_raw_fraction,
)

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.plugins.windows.agent_based.libwmi import parse_wmi_table

check_info = {}

dotnet_clrmemory_defaultlevels = {
    "upper": (10.0, 15.0)  # 10.0 percent specified by customer,
    # various sources (including MS) give
    # around 5-10% as healthy values
}


def check_dotnet_clrmemory(item, params, parsed):
    yield from wmi_yield_raw_fraction(
        parsed[""], item, "PercentTimeinGC", infoname="Time in GC", perfvar="percent", levels=params
    )


def discover_dotnet_clrmemory(parsed):
    return inventory_wmi_table_instances(
        parsed, filt=wmi_filter_global_only, levels=dotnet_clrmemory_defaultlevels
    )


check_info["dotnet_clrmemory"] = LegacyCheckDefinition(
    name="dotnet_clrmemory",
    parse_function=parse_wmi_table,
    service_name="DotNet Memory Management %s",
    discovery_function=discover_dotnet_clrmemory,
    check_function=check_dotnet_clrmemory,
    check_ruleset_name="clr_memory",
)
