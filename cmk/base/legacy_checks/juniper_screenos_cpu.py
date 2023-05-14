#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info, factory_settings
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.juniper import DETECT_JUNIPER_SCREENOS

factory_settings["juniper_screenos_cpu_default_levels"] = {"util": (80.0, 90.0)}


def inventory_juniper_screenos_cpu(info):
    yield None, {}


def check_juniper_screenos_cpu(_no_item, params, info):
    util1, util15 = map(float, info[0])
    warn, crit = params.get("util", (None, None)) if isinstance(params, dict) else params
    label15 = ""
    state = 0
    if util15 >= crit:
        state = 2
        label15 = "(!!)"
    elif util15 >= warn:
        state = max(state, 1)
        label15 = "(!)"

    perf = [
        ("util1", util1, warn, crit),
        ("util15", util15, warn, crit),
    ]

    message = "%d%% 1min, %d%% 15min%s (warn/crit at %d%%/%d%%)" % (
        util1,
        util15,
        label15,
        warn,
        crit,
    )
    return state, message, perf


check_info["juniper_screenos_cpu"] = LegacyCheckDefinition(
    detect=DETECT_JUNIPER_SCREENOS,
    check_function=check_juniper_screenos_cpu,
    discovery_function=inventory_juniper_screenos_cpu,
    check_ruleset_name="cpu_utilization",
    service_name="CPU utilization",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3224.16.1",
        oids=["2", "4"],
    ),
    default_levels_variable="juniper_screenos_cpu_default_levels",
)
