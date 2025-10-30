#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Original author: thl-cmk[at]outlook[dot]com

from collections.abc import Mapping

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    StringTable,
    check_levels,
    render,
)

from cmk_addons.plugins.meraki.lib.utils import load_json


# sample agent output
# {"perfScore": 1}
# sample string_table
# [['[{"perfScore": 0}]']]
# [['[{"perfScore": 12.0}]']]
# [['[{"perfScore": 0.00021434677238992957}]']]
def parse_appliance_performance(string_table: StringTable) -> float | None:
    json_data = load_json(string_table)

    try:
        return float(json_data[0]['perfScore'])
    except (ValueError, TypeError, KeyError):
        return None


agent_section_meraki_org_appliance_performance = AgentSection(
    name="cisco_meraki_org_appliance_performance",
    parse_function=parse_appliance_performance,
)


def discover_appliance_performance(section: float) -> DiscoveryResult:
    yield Service()


def check_appliance_performance(params: Mapping[str, any], section: float) -> CheckResult:
    yield from check_levels(
        value=section,
        label='Utilization',
        levels_upper=params['levels_upper'],
        render_func=render.percent,
        metric_name='utilization',
        boundaries=(0, 100),
    )


check_plugin_meraki_org_appliance_performance = CheckPlugin(
    name="cisco_meraki_org_appliance_performance",
    service_name="Utilization",
    check_function=check_appliance_performance,
    discovery_function=discover_appliance_performance,
    check_ruleset_name="cisco_meraki_org_appliance_performance",
    check_default_parameters={
        'levels_upper': ('fixed', (60, 80)),
    },
)
