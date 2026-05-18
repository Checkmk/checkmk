#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<citrix_serverload>>>
# 100


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    State,
    StringTable,
)


def parse_citrix_serverload(string_table: StringTable) -> StringTable:
    return string_table


def discover_citrix_serverload(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_citrix_serverload(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    try:
        load = int(section[0][0])
    except (IndexError, ValueError):
        return

    if load == 20000:
        yield Result(state=State.WARN, summary="License error")
        load = 10000

    yield from check_levels_v1(
        load / 100.0,
        metric_name="citrix_load",
        levels_upper=params["levels"],
        render_func=render.percent,
        label="Current Citrix Load",
    )


agent_section_citrix_serverload = AgentSection(
    name="citrix_serverload",
    parse_function=parse_citrix_serverload,
)


check_plugin_citrix_serverload = CheckPlugin(
    name="citrix_serverload",
    service_name="Citrix Serverload",
    discovery_function=discover_citrix_serverload,
    check_function=check_citrix_serverload,
    check_ruleset_name="citrix_load",
    check_default_parameters={
        "levels": (85.0, 95.0),
    },
)
