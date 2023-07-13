#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.bvip import DETECT_BVIP


def inventory_bvip_info(info):
    if info:
        return [(None, None)]
    return []


def check_bvip_info(_no_item, _no_params, info):
    unit_name, unit_id = info[0]
    if unit_name == unit_id:
        return 0, "Unit Name/ID: " + unit_name
    return 0, "Unit Name: %s, Unit ID: %s" % (unit_name, unit_id)


check_info["bvip_info"] = LegacyCheckDefinition(
    detect=DETECT_BVIP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3967.1.1.1",
        oids=["1", "2"],
    ),
    service_name="System Info",
    discovery_function=inventory_bvip_info,
    check_function=check_bvip_info,
)
