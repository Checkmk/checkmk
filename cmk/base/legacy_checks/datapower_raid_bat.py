#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.datapower import DETECT


def inventory_datapower_raid_bat(info):
    for controller_id, _bat_type, _serial, _name, _status in info:
        yield controller_id, None


def check_datapower_raid_bat(item, _no_params, info):
    datapower_raid_bat_status = {
        "1": (0, "charging"),
        "2": (1, "discharging"),
        "3": (2, "i2c errors detected"),
        "4": (0, "learn cycle active"),
        "5": (2, "learn cycle failed"),
        "6": (0, "learn cycle requested"),
        "7": (2, "learn cycle timeout"),
        "8": (2, "pack missing"),
        "9": (2, "temperature high"),
        "10": (2, "voltage low"),
        "11": (1, "periodic learn required"),
        "12": (1, "remaining capacity low"),
        "13": (2, "replace pack"),
        "14": (0, "normal"),
        "15": (1, "undefined"),
    }
    datapower_raid_bat_type = {
        "1": "no battery present",
        "2": "ibbu",
        "3": "bbu",
        "4": "zcrLegacyBBU",
        "5": "itbbu3",
        "6": "ibbu08",
        "7": "unknown",
    }
    for controller_id, bat_type, serial, name, status in info:
        if item == controller_id:
            state, state_txt = datapower_raid_bat_status[status]
            type_txt = datapower_raid_bat_type[bat_type]
            infotext = "Status: {}, Name: {}, Type: {}, Serial: {}".format(
                state_txt,
                name,
                type_txt,
                serial,
            )
            return state, infotext
    return None


def parse_datapower_raid_bat(string_table: StringTable) -> StringTable:
    return string_table


check_info["datapower_raid_bat"] = LegacyCheckDefinition(
    parse_function=parse_datapower_raid_bat,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.14685.3.1.258.1",
        oids=["1", "2", "3", "4", "5"],
    ),
    service_name="Raid Battery %s",
    discovery_function=inventory_datapower_raid_bat,
    check_function=check_datapower_raid_bat,
)
