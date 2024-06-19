#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.dell import DETECT_CHASSIS


def saveint(i: str) -> int:
    """Tries to cast a string to an integer and return it. In case this
    fails, it returns 0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0 back from this function,
    you can not know whether it is really 0 or something went wrong."""
    try:
        return int(i)
    except (TypeError, ValueError):
        return 0


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
            infotext = f"Status: {state_txt}, Name: {name}, ServiceTag: {service_tag}"

            return state, infotext

    return 3, "unknown slot"


def parse_dell_chassis_slots(string_table: StringTable) -> StringTable:
    return string_table


check_info["dell_chassis_slots"] = LegacyCheckDefinition(
    parse_function=parse_dell_chassis_slots,
    detect=DETECT_CHASSIS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.674.10892.2.5.1.1",
        oids=["2", "3", "4", "5"],
    ),
    service_name="Slot %s",
    discovery_function=inventory_dell_chassis_slots,
    check_function=check_dell_chassis_slots,
)
