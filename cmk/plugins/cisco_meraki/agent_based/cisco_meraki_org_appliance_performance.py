#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Original author: thl-cmk[at]outlook[dot]com

import json
from typing import TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    FixedLevelsT,
    render,
    Service,
    StringTable,
)

type Section = float


def parse_appliance_performance(string_table: StringTable) -> Section | None:
    match string_table:
        case [[payload]] if payload:
            return float(json.loads(payload)[0]["perfScore"])
        case _:
            return None


agent_section_meraki_org_appliance_performance = AgentSection(
    name="cisco_meraki_org_appliance_performance",
    parse_function=parse_appliance_performance,
)


def discover_appliance_performance(section: Section) -> DiscoveryResult:
    yield Service()


class CheckParams(TypedDict):
    levels_upper: FixedLevelsT[int]


def check_appliance_performance(params: CheckParams, section: Section) -> CheckResult:
    yield from check_levels(
        value=section,
        label="Utilization",
        levels_upper=params["levels_upper"],
        render_func=render.percent,
        metric_name="utilization",
        boundaries=(0, 100),
    )


check_plugin_cisco_meraki_org_appliance_performance = CheckPlugin(
    name="cisco_meraki_org_appliance_performance",
    service_name="Device utilization",
    check_function=check_appliance_performance,
    discovery_function=discover_appliance_performance,
    check_ruleset_name="cisco_meraki_org_appliance_performance",
    check_default_parameters={"levels_upper": ("fixed", (60, 80))},
)
