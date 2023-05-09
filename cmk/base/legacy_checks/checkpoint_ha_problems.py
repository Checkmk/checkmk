#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.checkpoint import DETECT


def inventory_checkpoint_ha_problems(info):
    for name, _dev_status, _description in info:
        yield name, None


def check_checkpoint_ha_problems(item, params, info):
    for name, dev_status, description in info:
        if name == item:
            if dev_status == "OK":
                return 0, "OK"
            return 2, "%s - %s" % (dev_status, description)
    return None


check_info["checkpoint_ha_problems"] = {
    "detect": DETECT,
    "check_function": check_checkpoint_ha_problems,
    "discovery_function": inventory_checkpoint_ha_problems,
    "service_name": "HA Problem %s",
    "fetch": SNMPTree(
        base=".1.3.6.1.4.1.2620.1.5.13.1",
        oids=["2", "3", "6"],
    ),
}
