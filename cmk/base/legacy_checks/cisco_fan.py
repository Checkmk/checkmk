#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import OIDEnd, SNMPTree, StringTable
from cmk.plugins.lib.cisco import DETECT_CISCO
from cmk.plugins.lib.cisco_sensor_item import cisco_sensor_item

cisco_fan_state_mapping = {
    "1": (0, "normal"),
    "2": (1, "warning"),
    "3": (2, "critical"),
    "4": (2, "shutdown"),
    "5": (3, "not present"),
    "6": (2, "not functioning"),
}


def inventory_cisco_fan(info):
    return [
        (cisco_sensor_item(line[0], line[-1]), None)
        for line in info
        if line[1] in ["1", "2", "3", "4", "6"]
    ]


def check_cisco_fan(item, params, info):
    for statustext, dev_state, oid_end in info:
        if cisco_sensor_item(statustext, oid_end) == item:
            state, state_readable = cisco_fan_state_mapping.get(
                dev_state, (3, "unknown[%s]" % dev_state)
            )
            yield state, "Status: %s" % state_readable


def parse_cisco_fan(string_table: StringTable) -> StringTable:
    return string_table


check_info["cisco_fan"] = LegacyCheckDefinition(
    parse_function=parse_cisco_fan,
    detect=DETECT_CISCO,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.13.1.4.1",
        oids=["2", "3", OIDEnd()],
    ),
    service_name="FAN %s",
    discovery_function=inventory_cisco_fan,
    check_function=check_cisco_fan,
)
