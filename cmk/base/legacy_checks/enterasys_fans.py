#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import OIDEnd, SNMPTree, StringTable
from cmk.plugins.lib.enterasys import DETECT_ENTERASYS

check_info = {}


def inventory_enterasys_fans(info):
    return [(x[0], None) for x in info if x[1] != "2"]


def check_enterasys_fans(item, _no_params, info):
    fan_states = {
        "1": "info not available",
        "2": "not installed",
        "3": "installed and operating",
        "4": "installed and not operating",
    }
    for num, state in info:
        if num == item:
            message = "FAN State: %s" % (fan_states[state])
            if state in ["1", "2"]:
                return 3, message
            if state == "4":
                return 2, message
            return 0, message
    return None


def parse_enterasys_fans(string_table: StringTable) -> StringTable:
    return string_table


check_info["enterasys_fans"] = LegacyCheckDefinition(
    name="enterasys_fans",
    parse_function=parse_enterasys_fans,
    detect=DETECT_ENTERASYS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.52.4.3.1.3.1.1",
        oids=[OIDEnd(), "2"],
    ),
    service_name="FAN %s",
    discovery_function=inventory_enterasys_fans,
    check_function=check_enterasys_fans,
)
