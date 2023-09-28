#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.decru import DETECT_DECRU


def inventory_decru_power(info):
    return [(l[0], None) for l in info]


def check_decru_power(item, params, info):
    for power in info:
        if power[0] == item:
            if power[1] != "1":
                return (2, "power supply in state %s" % power[1])
            return (0, "power supply ok")

    return (3, "power supply not found")


check_info["decru_power"] = LegacyCheckDefinition(
    detect=DETECT_DECRU,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12962.1.2.6.1",
        oids=["2", "3"],
    ),
    service_name="POWER %s",
    discovery_function=inventory_decru_power,
    check_function=check_decru_power,
)
