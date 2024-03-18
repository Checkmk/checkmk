#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.blade import DETECT_BLADE_BX


def inventory_blade_bx_blades(info):
    for id_, status, _serial, _name in info:
        if status != "3":  # blade not present
            yield id_, None


def check_blade_bx_blades(item, _no_params, info):
    status_codes = {
        "1": (3, "unknown"),
        "2": (0, "OK"),
        "3": (3, "not present"),
        "4": (2, "error"),
        "5": (2, "critical"),
        "6": (0, "standby"),
    }

    for id_, status, serial, name in info:
        if id_ == item:
            state, state_readable = status_codes[status]
            if name:
                name_info = f"[{name}, Serial: {serial}]"
            else:
                name_info = "[Serial: %s]" % serial
            return state, f"{name_info} Status: {state_readable}"
    return None


def parse_blade_bx_blades(string_table: StringTable) -> StringTable:
    return string_table


check_info["blade_bx_blades"] = LegacyCheckDefinition(
    parse_function=parse_blade_bx_blades,
    detect=DETECT_BLADE_BX,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.7244.1.1.1.4.2.1.1",
        oids=["1", "2", "5", "21"],
    ),
    service_name="Blade %s",
    discovery_function=inventory_blade_bx_blades,
    check_function=check_blade_bx_blades,
)
