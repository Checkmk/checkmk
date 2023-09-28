#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.checkpoint import DETECT


def inventory_checkpoint_powersupply(info):
    for index, _dev_status in info:
        yield index, {}


def check_checkpoint_powersupply(item, params, info):
    for index, dev_status in info:
        if index == item:
            status = 0
            # found no documentation on possible power supply status,
            # "Up" is the only one observed so far
            if dev_status != "Up":
                status = 2
            return status, dev_status
    return None


check_info["checkpoint_powersupply"] = LegacyCheckDefinition(
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2620.1.6.7.9.1.1",
        oids=["1", "2"],
    ),
    service_name="Power Supply %s",
    discovery_function=inventory_checkpoint_powersupply,
    check_function=check_checkpoint_powersupply,
)
