#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# FIXME:
# - no camel case in check parameters
# - use friendly output of values. Output
#   "Ingress Dequeue Packets" instead of "brcdTMStatsIngressDequeuePkts"


import re
import time

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import get_rate, get_value_store, SNMPTree, StringTable
from cmk.plugins.brocade.lib import DETECT_MLX

LEVELS = {
    "brcdTMStatsTotalIngressPktsCnt": (1000, 10000),
    "brcdTMStatsIngressEnqueuePkts": (1000, 10000),
    "brcdTMStatsEgressEnqueuePkts": (1000, 10000),
    "brcdTMStatsIngressDequeuePkts": (1000, 10000),
    "brcdTMStatsIngressTotalQDiscardPkts": (1000, 10000),
    "brcdTMStatsIngressOldestDiscardPkts": (1000, 10000),
    "brcdTMStatsEgressDiscardPkts": (1000, 10000),
}


check_info = {}


def discover_brocade_tm(info):
    inventory = []
    for line in info:
        inventory.append((line[0], None))
    return inventory


def check_brocade_tm(item, _no_params, info):
    for line in info:
        if line[0] == item:
            tm = {}

            tm["TotalIngressPktsCnt"] = line[1]
            tm["IngressEnqueuePkts"] = line[2]
            tm["EgressEnqueuePkts"] = line[3]
            tm["IngressDequeuePkts"] = line[4]
            tm["IngressTotalQDiscardPkts"] = line[5]
            tm["IngressOldestDiscardPkts"] = line[6]
            tm["EgressDiscardPkts"] = line[7]

            now = time.time()
            infotext = ""
            perfdata = []
            overall_state = 0

            value_store = get_value_store()
            for name, counter in tm.items():
                rate = get_rate(
                    value_store, f"{name}.{item}", now, int(counter), raise_overflow=True
                )

                warn, crit = LEVELS["brcdTMStats" + name]
                if re.search("Discard", name):
                    if rate > crit:
                        state = 2
                        sym = "(!!)"
                    elif rate > warn:
                        state = 1
                        sym = "(!)"
                    else:
                        state = 0
                        sym = ""
                else:
                    state = 0
                    sym = ""
                infotext += f"{name}: {rate:.1f}{sym}, "
                perfdata.append((name, rate, warn, crit))
                overall_state = max(overall_state, state)

            return (overall_state, infotext, perfdata)

    return (3, "Interface not found")


def parse_brocade_tm(string_table: StringTable) -> StringTable:
    return string_table


check_info["brocade_tm"] = LegacyCheckDefinition(
    name="brocade_tm",
    parse_function=parse_brocade_tm,
    detect=DETECT_MLX,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1991.1.14.2.1.2.2.1",
        oids=["3", "4", "5", "6", "9", "11", "13", "15"],
    ),
    service_name="TM %s",
    discovery_function=discover_brocade_tm,
    check_function=check_brocade_tm,
)
