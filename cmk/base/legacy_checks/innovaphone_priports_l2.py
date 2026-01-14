#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import equals, SNMPTree, StringTable

check_info = {}


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


def discover_innovaphone_priports_l2(info):
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

            return (
                state,
                f"State: {states[l2state]}{state_label}, Mode: {modes[l2mode]}{mode_label}",
            )
    return 3, "Output not found"


def parse_innovaphone_priports_l2(string_table: StringTable) -> StringTable:
    return string_table


check_info["innovaphone_priports_l2"] = LegacyCheckDefinition(
    name="innovaphone_priports_l2",
    parse_function=parse_innovaphone_priports_l2,
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.6666"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.6666.1.1.1",
        oids=["1", "2", "3"],
    ),
    service_name="Port L2 %s",
    discovery_function=discover_innovaphone_priports_l2,
    check_function=check_innovaphone_priports_l2,
    check_default_parameters={},
)
