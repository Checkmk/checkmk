#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.config import check_info, factory_settings
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.bluecat import DETECT_BLUECAT

factory_settings["bluecat_ha"] = {
    "oper_states": {
        "warning": [5, 6, 7],
        "critical": [8, 4],
    },
}


def inventory_bluecat_ha(info):
    # Only add if device is not in standalone mode
    if info[0][0] != "1":
        return [(None, None)]
    return []


def check_bluecat_ha(item, params, info):
    oper_state = int(info[0][0])
    oper_states = {
        1: "standalone",
        2: "active",
        3: "passiv",
        4: "stopped",
        5: "stopping",
        6: "becoming active",
        7: "becomming passive",
        8: "fault",
    }

    state = 0
    if oper_state in params["oper_states"]["warning"]:
        state = 1
    elif oper_state in params["oper_states"]["critical"]:
        state = 2
    yield state, "State is %s" % oper_states[oper_state]


check_info["bluecat_ha"] = {
    "detect": DETECT_BLUECAT,
    "check_function": check_bluecat_ha,
    "discovery_function": inventory_bluecat_ha,
    "service_name": "HA State",
    "default_levels_variable": "bluecat_ha",
    "check_ruleset_name": "bluecat_ha",
    "fetch": SNMPTree(
        base=".1.3.6.1.4.1.13315.3.1.5.2.1",
        oids=["1"],
    ),
}
