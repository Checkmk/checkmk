#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition, savefloat
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree
from cmk.agent_based.v2.type_defs import StringTable
from cmk.plugins.lib.juniper import DETECT_JUNIPER_TRPZ


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


def parse_juniper_trpz_cpu_util(string_table: StringTable) -> StringTable:
    return string_table


check_info["juniper_trpz_cpu_util"] = LegacyCheckDefinition(
    parse_function=parse_juniper_trpz_cpu_util,
    detect=DETECT_JUNIPER_TRPZ,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.14525.4.8.1.1.11",
        oids=["1", "2", "3"],
    ),
    service_name="CPU utilization",
    discovery_function=inventory_juniper_trpz_cpu_util,
    check_function=check_juniper_trpz_cpu_util,
    check_ruleset_name="cpu_utilization",
    check_default_parameters={"util": (80.0, 90.0)},
)
