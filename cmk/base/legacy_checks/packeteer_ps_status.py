#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree, startswith


def inventory_packeteer_ps_status(info):
    if info:
        return [(None, None)]
    return []


def check_packeteer_ps_status(_no_item, _no_params, info):
    for nr, ps_status in enumerate(info[0]):
        if ps_status == "1":
            yield 0, "Power Supply %d okay" % nr
        else:
            yield 2, "Power Supply %d not okay" % nr


check_info["packeteer_ps_status"] = LegacyCheckDefinition(
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.2334"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2334.2.1.5",
        oids=["8", "10"],
    ),
    service_name="Power Supply Status",
    discovery_function=inventory_packeteer_ps_status,
    check_function=check_packeteer_ps_status,
)
