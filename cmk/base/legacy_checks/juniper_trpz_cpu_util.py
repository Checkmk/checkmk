#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition, savefloat
from cmk.base.config import check_info, factory_settings
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.juniper import DETECT_JUNIPER_TRPZ

factory_settings["juniper_trpz_cpu_util_default_levels"] = {"util": (80.0, 90.0)}


def inventory_juniper_trpz_cpu_util(info):
    yield None, {}


def check_juniper_trpz_cpu_util(_no_item, params, info):
    utilc, util1, util5 = map(savefloat, info[0])

    warn, crit = params.get("util", (None, None)) if isinstance(params, dict) else params

    label1, label5 = "", ""
    state = 0

    if util1 >= crit:
        state = 2
        label1 = "(!!)"
    elif util1 >= warn:
        state = 1
        label1 = "(!)"

    if util5 >= crit:
        state = 2
        label5 = "(!!)"
    elif util5 >= warn:
        state = max(state, 1)
        label5 = "(!)"

    perf = [
        ("util1", util1, warn, crit),
        ("util5", util5, warn, crit),
        ("utilc", utilc),
    ]

    message = "%d%% current, %d%% 1min%s, %d%% 5min%s" % (utilc, util1, label1, util5, label5)

    return state, message, perf


check_info["juniper_trpz_cpu_util"] = LegacyCheckDefinition(
    detect=DETECT_JUNIPER_TRPZ,
    check_function=check_juniper_trpz_cpu_util,
    discovery_function=inventory_juniper_trpz_cpu_util,
    check_ruleset_name="cpu_utilization",
    service_name="CPU utilization",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.14525.4.8.1.1.11",
        oids=["1", "2", "3"],
    ),
    default_levels_variable="juniper_trpz_cpu_util_default_levels",
    check_default_parameters={"util": (80.0, 90.0)},
)
