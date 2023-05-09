#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import saveint
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.dell import DETECT_CHASSIS


def inventory_dell_chassis_slots(info):
    inventory = []
    for line in info:
        number = line[3]
        if saveint(number) in (1, 2, 3, 4, 5, 6, 7, 8, 9):
            number = "0" + number
        if line[0] != "1" and line[2] != "N/A":
            inventory.append((number, None))
    return inventory


def check_dell_chassis_slots(item, _no_params, info):
    for status, service_tag, name, number in info:
        if saveint(number) in (1, 2, 3, 4, 5, 6, 7, 8, 9):
            number = "0" + number
        if item == number:
            # absent = 1,none = 2,basic = 3,off = 4,
            state_table = {
                "1": ("absent", 0),
                "2": ("none", 1),
                "3": ("basic", 0),
                "4": ("off", 1),
            }
            state_txt, state = state_table.get(status, ("unknown state, ", 3))
            infotext = "Status: %s, Name: %s, ServiceTag: %s" % (state_txt, name, service_tag)

            return state, infotext

    return 3, "unknown slot"


check_info["dell_chassis_slots"] = {
    "detect": DETECT_CHASSIS,
    "check_function": check_dell_chassis_slots,
    "discovery_function": inventory_dell_chassis_slots,
    "service_name": "Slot %s",
    "fetch": SNMPTree(
        base=".1.3.6.1.4.1.674.10892.2.5.1.1",
        oids=["2", "3", "4", "5"],
    ),
}
