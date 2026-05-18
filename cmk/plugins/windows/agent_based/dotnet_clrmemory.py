#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Service,
)
from cmk.plugins.windows.agent_based.libwmi import parse_wmi_table, WMISection
from cmk.plugins.windows.agent_based.libwmi_legacy import (
    inventory_wmi_table_instances,
    wmi_calculate_raw_average,
)


def _wmi_filter_global_only(
    tables: WMISection,
    row: str | int,
) -> bool:
    for table in tables.values():
        try:
            value = table.get(row, "Name")
        except KeyError:
            return False
        if value != "_Global_":
            return False
    return True


def discover_dotnet_clrmemory(section: WMISection) -> DiscoveryResult:
    for item, _parameters in inventory_wmi_table_instances(
        section, filt=_wmi_filter_global_only, levels={}
    ):
        yield Service(item=item)


def check_dotnet_clrmemory(
    item: str, params: Mapping[str, Any], section: WMISection
) -> CheckResult:
    try:
        average = wmi_calculate_raw_average(section[""], item, "PercentTimeinGC", 100)
    except KeyError:
        return

    yield from check_levels_v1(
        average,
        metric_name="percent",
        levels_upper=params["upper"],
        label="Time spent in Garbage Collection",
        render_func=render.percent,
        boundaries=(0, 100),
    )


agent_section_dotnet_clrmemory = AgentSection(
    name="dotnet_clrmemory",
    parse_function=parse_wmi_table,
)


check_plugin_dotnet_clrmemory = CheckPlugin(
    name="dotnet_clrmemory",
    service_name="DotNet Memory Management %s",
    discovery_function=discover_dotnet_clrmemory,
    check_function=check_dotnet_clrmemory,
    check_ruleset_name="clr_memory",
    check_default_parameters={
        "upper": (10.0, 15.0)  # 10.0 percent specified by customer,
        # various sources (including MS) give
        # around 5-10% as healthy values
    },
)
