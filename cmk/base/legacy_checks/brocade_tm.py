#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# FIXME:
# - no camel case in check parameters
# - use friendly output of values. Output
#   "Ingress Dequeue Packets" instead of "brcdTMStatsIngressDequeuePkts"


import re
import time

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import get_rate, get_value_store, SNMPTree
from cmk.base.plugins.agent_based.utils.brocade import DETECT_MLX


def inventory_brocade_tm(info):
    inventory = []
    for line in info:
        inventory.append((line[0], None))
    return inventory


def check_brocade_tm(item, params, info):
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

                warn, crit = params["brcdTMStats" + name]
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
                infotext += "%s: %.1f%s, " % (name, rate, sym)
                perfdata.append((name, rate, warn, crit))
                overall_state = max(overall_state, state)

            return (overall_state, infotext, perfdata)

    return (3, "Interface not found")


check_info["brocade_tm"] = LegacyCheckDefinition(
    detect=DETECT_MLX,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1991.1.14.2.1.2.2.1",
        oids=["3", "4", "5", "6", "9", "11", "13", "15"],
    ),
    service_name="TM %s",
    discovery_function=inventory_brocade_tm,
    check_function=check_brocade_tm,
    check_ruleset_name="brocade_tm",
    check_default_parameters={
        "brcdTMStatsTotalIngressPktsCnt": (1000, 10000),
        "brcdTMStatsIngressEnqueuePkts": (1000, 10000),
        "brcdTMStatsEgressEnqueuePkts": (1000, 10000),
        "brcdTMStatsIngressDequeuePkts": (1000, 10000),
        "brcdTMStatsIngressTotalQDiscardPkts": (1000, 10000),
        "brcdTMStatsIngressOldestDiscardPkts": (1000, 10000),
        "brcdTMStatsEgressDiscardPkts": (1000, 10000),
    },
)
