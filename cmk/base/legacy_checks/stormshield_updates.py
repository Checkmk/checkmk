#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.stormshield import DETECT_STORMSHIELD


def inventory_stormshield_updates(info):
    for subsystem, state, lastrun in info:
        if state == "Failed" and lastrun == "":
            pass
        elif not state in ["Not Available", "Never started"]:
            yield subsystem, {}


def check_stormshield_updates(item, params, info):
    for subsystem, state, lastrun in info:
        if item == subsystem:
            if lastrun == "":
                lastrun = "Never"
            infotext = f"Subsystem {subsystem} is {state}, last update: {lastrun}"
            monitoringstate = params.get(state, 3)
            yield monitoringstate, infotext


check_info["stormshield_updates"] = LegacyCheckDefinition(
    detect=DETECT_STORMSHIELD,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11256.1.9.1.1",
        oids=["2", "3", "4"],
    ),
    service_name="Autoupdate %s",
    discovery_function=inventory_stormshield_updates,
    check_function=check_stormshield_updates,
    check_ruleset_name="stormshield_updates",
    check_default_parameters={
        "Not Available": 1,
        "Broken": 2,
        "Uptodate": 0,
        "Disabled": 1,
        "Never started": 0,
        "Running": 0,
        "Failed": 2,
    },
)
