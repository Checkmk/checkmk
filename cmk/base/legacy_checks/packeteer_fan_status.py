#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree, startswith


def inventory_packeteer_fan_status(info):
    for nr, fan_status in enumerate(info[0]):
        if fan_status in ["1", "2"]:
            yield ("%d" % nr, None)


def check_packeteer_fan_status(item, _no_params, info):
    fan_status = info[0][int(item)]
    if fan_status == "1":
        return 0, "OK"
    if fan_status == "2":
        return 2, "Not OK"
    if fan_status == "3":
        return 2, "Not present"
    return None


check_info["packeteer_fan_status"] = LegacyCheckDefinition(
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.2334"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2334.2.1.5",
        oids=["12", "14", "22", "24"],
    ),
    service_name="Fan Status",
    discovery_function=inventory_packeteer_fan_status,
    check_function=check_packeteer_fan_status,
)
