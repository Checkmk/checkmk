#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.dell import DETECT_CHASSIS


def inventory_dell_chassis_status(info):
    if info:
        return [(None, None)]
    return []


def check_dell_chassis_status(item, _no_params, info):
    whats = [
        "URL",
        "Locaction",
        "Name",
        "Service Tag",
        "Data Center",
        "Firmware Version",
        "Status",
    ]

    state_table = {
        "1": ("Other, ", 1),
        "2": ("Unknown, ", 1),
        "3": ("OK", 0),
        "4": ("Non-Critical, ", 1),
        "5": ("Critical, ", 2),
        "6": ("Non-Recoverable, ", 2),
    }

    for what, value in zip(whats, info[0]):
        if what == "Status":
            descr, status = state_table[value]
            yield status, what + ": " + descr
        else:
            yield 0, what + ": " + value


def parse_dell_chassis_status(string_table: StringTable) -> StringTable:
    return string_table


check_info["dell_chassis_status"] = LegacyCheckDefinition(
    parse_function=parse_dell_chassis_status,
    detect=DETECT_CHASSIS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.674.10892.2",
        oids=["1.1.7", "1.1.9", "1.1.10", "1.1.11", "1.1.15", "1.2.1", "2.1"],
    ),
    service_name="Chassis Health",
    discovery_function=inventory_dell_chassis_status,
    check_function=check_dell_chassis_status,
)
