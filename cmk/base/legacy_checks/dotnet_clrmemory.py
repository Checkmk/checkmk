#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.legacy.v0_unstable import (
    check_levels,
    LegacyCheckDefinition,
    LegacyCheckResult,
)
from cmk.agent_based.v2 import render
from cmk.base.check_legacy_includes.wmi import (
    inventory_wmi_table_instances,
    wmi_calculate_raw_average,
    wmi_filter_global_only,
)
from cmk.plugins.windows.agent_based.libwmi import parse_wmi_table, WMISection

check_info = {}


def check_dotnet_clrmemory(
    item: str, params: Mapping[str, Any], parsed: WMISection
) -> LegacyCheckResult:
    try:
        average = wmi_calculate_raw_average(parsed[""], item, "PercentTimeinGC", 100)
    except KeyError:
        return

    yield check_levels(
        average,
        "percent",
        params["upper"],
        infoname="Time spent in Garbage Collection",
        human_readable_func=render.percent,
        boundaries=(0, 100),
    )


def discover_dotnet_clrmemory(parsed):
    return inventory_wmi_table_instances(parsed, filt=wmi_filter_global_only, levels={})


check_info["dotnet_clrmemory"] = LegacyCheckDefinition(
    name="dotnet_clrmemory",
    parse_function=parse_wmi_table,
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
