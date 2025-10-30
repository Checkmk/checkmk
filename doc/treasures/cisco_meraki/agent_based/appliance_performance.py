#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# License: GNU General Public License v2
#
# Author: thl-cmk[at]outlook[dot]com
# URL   : https://thl-cmk.hopto.org
# Date  : 2024-06-20
# File  : appliance_performance.py (check plugin)

# 2024-06-29: refactored for CMK 2.3
# 2024-06-30: renamed from cisco_meraki_org_appliance_performance.py in to appliance_performance.py
# 2024-08-02: fixed if perfscore was float instead of int

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
