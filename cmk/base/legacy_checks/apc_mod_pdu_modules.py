#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition, savefloat, saveint
from cmk.base.config import check_info

from cmk.agent_based.v2 import equals, SNMPTree, StringTable


def inventory_apc_mod_pdu_modules(info):
    return [(x[0], None) for x in info if x[0] != ""]


def check_apc_mod_pdu_modules(item, _no_params, info):
    apc_states = {
        1: "normal",
        2: "warning",
        3: "notPresent",
        6: "unknown",
    }
    for name, status, current_power in info:
        if name == item:
            status = saveint(status)
            # As per the device's MIB, the values are measured in tenths of kW
            current_power = savefloat(current_power) / 10
            message = f"Status {apc_states.get(status, 6)}, current: {current_power:.2f} kW "

            perf = [("power", current_power * 1000)]
            if status == 2:
                return 1, message, perf
            if status in [3, 6]:
                return 2, message, perf
            if status == 1:
                return 0, message, perf
            return 3, message
    return 3, "Module not found"


def parse_apc_mod_pdu_modules(string_table: StringTable) -> StringTable:
    return string_table


check_info["apc_mod_pdu_modules"] = LegacyCheckDefinition(
    parse_function=parse_apc_mod_pdu_modules,
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.318.1.3.24.1"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.318.1.1.22.2.6.1",
        oids=["4", "6", "20"],
    ),
    service_name="Module %s",
    discovery_function=inventory_apc_mod_pdu_modules,
    check_function=check_apc_mod_pdu_modules,
)
