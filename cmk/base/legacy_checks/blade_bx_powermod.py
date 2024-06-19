#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.blade import DETECT_BLADE_BX


def inventory_blade_bx_powermod(info):
    for line in info:
        yield (line[0], None)


def check_blade_bx_powermod(item, _no_param, info):
    power_status = {
        "1": ("unknown", 3),
        "2": ("ok", 0),
        "3": ("not-present", 2),
        "4": ("error", 2),
        "5": ("critical", 2),
        "6": ("off", 2),
        "7": ("dummy", 2),
        "8": ("fanmodule", 0),
    }
    for line in info:
        index, status, product_name = line
        if not index == item:
            continue
        state_readable, state = power_status[status]
    return state, f"{product_name} Status is {state_readable}"


def parse_blade_bx_powermod(string_table: StringTable) -> StringTable:
    return string_table


check_info["blade_bx_powermod"] = LegacyCheckDefinition(
    parse_function=parse_blade_bx_powermod,
    detect=DETECT_BLADE_BX,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.7244.1.1.1.3.2.4.1",
        oids=["1", "2", "4"],
    ),
    service_name="Power Module %s",
    discovery_function=inventory_blade_bx_powermod,
    check_function=check_blade_bx_powermod,
)
