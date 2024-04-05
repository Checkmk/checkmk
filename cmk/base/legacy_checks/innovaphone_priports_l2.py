#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition, saveint
from cmk.base.config import check_info

from cmk.agent_based.v2 import equals, SNMPTree, StringTable


def inventory_innovaphone_priports_l2(info):
    inventory = []
    for line in info:
        if line[1] != "1":
            inventory.append((line[0], {"mode": saveint(line[2])}))
    return inventory


def check_innovaphone_priports_l2(item, params, info):
    modes = {
        1: "TE",
        2: "NT",
    }

    states = {
        1: "Down",
        2: "UP",
    }

    for line in info:
        if line[0] == item:
            state = 0
            l2state, l2mode = map(saveint, line[1:])
            state_label = ""
            if l2state == 1:
                state = 2
                state_label = "(!!)"

            mode_label = ""
            if l2mode != params["mode"]:
                state = 2
                mode_label = "(!!)"

            return state, "State: {}{}, Mode: {}{}".format(
                states[l2state],
                state_label,
                modes[l2mode],
                mode_label,
            )
    return 3, "Output not found"


def parse_innovaphone_priports_l2(string_table: StringTable) -> StringTable:
    return string_table


check_info["innovaphone_priports_l2"] = LegacyCheckDefinition(
    parse_function=parse_innovaphone_priports_l2,
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.6666"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.6666.1.1.1",
        oids=["1", "2", "3"],
    ),
    service_name="Port L2 %s",
    discovery_function=inventory_innovaphone_priports_l2,
    check_function=check_innovaphone_priports_l2,
    check_default_parameters={},
)
