#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.avaya import DETECT_AVAYA

avaya_chassis_card_operstatus_codes = {
    1: (0, "up"),
    2: (2, "down"),
    3: (0, "testing"),
    4: (3, "unknown"),
    5: (0, "dormant"),
}


def inventory_avaya_chassis_card(info):
    for line in info:
        yield line[0], None


def check_avaya_chassis_card(item, _no_params, info):
    for line in info:
        if line[0] == item:
            status, name = avaya_chassis_card_operstatus_codes[int(line[1])]
            return status, "Operational status: %s" % name
    return None


check_info["avaya_chassis_card"] = LegacyCheckDefinition(
    detect=DETECT_AVAYA,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2272.1.4.9.1.1",
        oids=["1", "6"],
    ),
    service_name="Card %s",
    discovery_function=inventory_avaya_chassis_card,
    check_function=check_avaya_chassis_card,
)
