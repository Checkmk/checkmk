#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info, factory_settings
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.bvip import DETECT_BVIP

factory_settings["bvip_poe_default_levels"] = {"levels": (50.0, 60.0)}


def inventory_bvip_poe(info):
    if not info:
        return []
    if info[0][0] != "0":
        return [(None, {})]
    return []


def check_bvip_poe(_no_item, params, info):
    warn, crit = params["levels"]
    watt = float(info[0][0]) / 10
    if watt >= crit:
        state = 2
    elif watt >= warn:
        state = 1
    else:
        state = 0
    return state, "%.3f W" % watt, [("power", watt)]


check_info["bvip_poe"] = LegacyCheckDefinition(
    detect=DETECT_BVIP,
    check_function=check_bvip_poe,
    discovery_function=inventory_bvip_poe,
    service_name="POE Power",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3967.1.1",
        oids=["10"],
    ),
    check_ruleset_name="epower_single",
    default_levels_variable="bvip_poe_default_levels",
    check_default_parameters={"levels": (50.0, 60.0)},
)
