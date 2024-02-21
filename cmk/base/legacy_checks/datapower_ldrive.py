#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.datapower import DETECT


def inventory_datapower_ldrive(info):
    for controller, ldrive, _raid_level, _num_drives, _status in info:
        item = f"{controller}-{ldrive}"
        yield item, None


def check_datapower_ldrive(item, _no_params, info):
    datapower_ldrive_status = {
        "1": (2, "offline"),
        "2": (2, "partially degraded"),
        "3": (2, "degraded"),
        "4": (0, "optimal"),
        "5": (1, "unknown"),
    }
    datapower_ldrive_raid = {
        "1": "0",
        "2": "1",
        "3": "1E",
        "4": "5",
        "5": "6",
        "6": "10",
        "7": "50",
        "8": "60",
        "9": "undefined",
    }
    for controller, ldrive, raid_level, num_drives, status in info:
        if item == f"{controller}-{ldrive}":
            state, state_txt = datapower_ldrive_status[status]
            raid_level = datapower_ldrive_raid[raid_level]
            infotext = "Status: {}, RAID Level: {}, Number of Drives: {}".format(
                state_txt,
                raid_level,
                num_drives,
            )
            return state, infotext
    return None


def parse_datapower_ldrive(string_table: StringTable) -> StringTable:
    return string_table


check_info["datapower_ldrive"] = LegacyCheckDefinition(
    parse_function=parse_datapower_ldrive,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.14685.3.1.259.1",
        oids=["1", "2", "4", "5", "6"],
    ),
    service_name="Logical Drive %s",
    discovery_function=inventory_datapower_ldrive,
    check_function=check_datapower_ldrive,
)
