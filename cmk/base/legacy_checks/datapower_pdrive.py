#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.datapower import DETECT


def inventory_datapower_pdrive(info):
    for controller, device, _ldrive, _position, status, _progress, _vendor, _product, _fail in info:
        if status != "12":
            item = f"{controller}-{device}"
            yield item, None


def check_datapower_pdrive(item, _no_params, info):
    datapower_pdrive_status = {
        "1": (0, "Unconfigured/Good"),
        "2": (0, "Unconfigured/Good/Foreign"),
        "3": (1, "Unconfigured/Bad"),
        "4": (1, "Unconfigured/Bad/Foreign"),
        "5": (0, "Hot spare"),
        "6": (1, "Offline"),
        "7": (2, "Failed"),
        "8": (1, "Rebuilding"),
        "9": (0, "Online"),
        "10": (1, "Copyback"),
        "11": (1, "System"),
        "12": (1, "Undefined"),
    }
    datapower_pdrive_fail = {
        "1": (2, "disk reports failure"),
        "2": (0, "disk reports no failure"),
    }
    datapower_pdrive_position = {
        "1": "HDD 0",
        "2": "HDD 1",
        "3": "HDD 2",
        "4": "HDD 3",
        "5": "undefined",
    }
    for controller, device, ldrive, position, status, progress, vendor, product, fail in info:
        if item == f"{controller}-{device}":
            member_of_ldrive = f"{controller}-{ldrive}"
            state, state_txt = datapower_pdrive_status[status]
            position_txt = datapower_pdrive_position[position]
            if int(progress) != 0:
                progress_txt = " - Progress: %s%%" % progress
            else:
                progress_txt = ""
            infotext = "{}{}, Position: {}, Logical Drive: {}, Product: {} {}".format(
                state_txt,
                progress_txt,
                position_txt,
                member_of_ldrive,
                vendor,
                product,
            )
            yield state, infotext

            if fail:
                yield datapower_pdrive_fail[fail]


def parse_datapower_pdrive(string_table: StringTable) -> StringTable:
    return string_table


check_info["datapower_pdrive"] = LegacyCheckDefinition(
    parse_function=parse_datapower_pdrive,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.14685.3.1.260.1",
        oids=["1", "2", "4", "6", "7", "8", "14", "15", "18"],
    ),
    service_name="Physical Drive %s",
    discovery_function=inventory_datapower_pdrive,
    check_function=check_datapower_pdrive,
)
