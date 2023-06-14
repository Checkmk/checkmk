#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.apc import DETECT

apc_inrow_airflow_default_levels = {
    "level_low": (500.0, 200.0),
    "level_high": (1000.0, 1100.0),
}


def inventory_apc_inrow_airflow(info):
    if info:
        return [(None, apc_inrow_airflow_default_levels)]
    return []


def check_apc_inrow_airflow(_no_item, params, info):
    # The MIB states that this value is given in hundredths of liters per second.
    # However, it appears that the device actually returns l/s, as the oom should
    # be closer to 1000 l/s. (cf. https://www.apc.com/salestools/DRON-AAAR53/DRON-AAAR53_R1_EN.pdf)
    try:
        flow = float(info[0][0])
    except Exception:
        return None

    state = 0
    message = ""

    warn, crit = params["level_low"]
    if flow < crit:
        state = 2
        message = "too low"
    elif flow < warn:
        state = 1
        message = "too low"

    warn, crit = params["level_high"]
    if flow >= crit:
        state = 2
        message = "too high"
    elif flow >= warn:
        state = 1
        message = "too high"

    perf = [("flow", flow, warn, crit)]
    return state, "Current: %.0f l/s %s" % (flow, message), perf


check_info["apc_inrow_airflow"] = LegacyCheckDefinition(
    detect=DETECT,
    check_function=check_apc_inrow_airflow,
    discovery_function=inventory_apc_inrow_airflow,
    service_name="Airflow",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.318.1.1.13.3.2.2.2",
        oids=["5"],
    ),
    check_ruleset_name="airflow",
)
