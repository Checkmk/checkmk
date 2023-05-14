#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.juniper import DETECT_JUNIPER_SCREENOS


def inventory_juniper_screenos_fan(info):
    # SNMP outputs "Fan 1". Our item is just '1'
    return [(line[0].split()[-1], None) for line in info]


def check_juniper_screenos_fan(item, params, info):
    for fan_id, fan_status in info:
        if fan_id.split()[-1] == item:
            if fan_status == "1":
                return (0, "status is good")
            if fan_status == "2":
                return (2, "status is failed")
            return (2, "Unknown fan status %s" % fan_status)
    return (3, "Sensor not found in SNMP data")


check_info["juniper_screenos_fan"] = LegacyCheckDefinition(
    detect=DETECT_JUNIPER_SCREENOS,
    check_function=check_juniper_screenos_fan,
    discovery_function=inventory_juniper_screenos_fan,
    service_name="FAN %s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3224.21.2.1",
        oids=["3", "2"],
    ),
)
