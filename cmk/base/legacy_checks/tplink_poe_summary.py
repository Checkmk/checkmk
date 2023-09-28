#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import check_levels, LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.tplink import DETECT_TPLINK


def inventory_tplink_poe_summary(info):
    if info and info[0][0] != "0":
        return [(None, {})]
    return []


def check_tplink_poe_summary(_no_item, params, info):
    deci_watt = float(info[0][0])
    watt = deci_watt / 10
    return check_levels(watt, "power", params.get("levels", (None, None)), unit="Watt")


check_info["tplink_poe_summary"] = LegacyCheckDefinition(
    detect=DETECT_TPLINK,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11863.6.56.1.1.1",
        oids=["3"],
    ),
    service_name="POE Power",
    discovery_function=inventory_tplink_poe_summary,
    check_function=check_tplink_poe_summary,
    check_ruleset_name="epower_single",
)
