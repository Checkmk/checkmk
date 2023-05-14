#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.ra32e import DETECT_RA32E


def inventory_ra32e_power(info):
    if info[0][0]:
        return [(None, {})]
    return None


def check_ra32e_power(item, params, info):
    power = info[0][0]

    if power == "1":
        return 0, "unit is running on AC/Utility power"
    if power == "0":
        return 1, "unit is running on battery backup power"
    return 3, "unknown status"


check_info["ra32e_power"] = LegacyCheckDefinition(
    detect=DETECT_RA32E,
    discovery_function=inventory_ra32e_power,
    check_function=check_ra32e_power,
    service_name="Power Supply",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.20916.1.8.1.1.3",
        oids=["1"],
    ),
)
