#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.apc import DETECT


def inventory_apc_inputs(info):
    yield from ((line[0], {"state": line[2]}) for line in info if line[2] not in ["3", "4"])


def check_apc_inputs(item, params, info):
    states = {
        "1": "closed",
        "2": "open",
        "3": "disabled",
        "4": "not applicable",
    }
    alarm_states = {
        "1": "normal",
        "2": "warning",
        "3": "critical",
        "4": "not applicable",
    }
    for name, _location, state, alarm_status in info:
        if name == item:
            if alarm_status in ["2", "4"]:
                check_state = 1
            elif alarm_status == "3":
                check_state = 2
            elif alarm_status == "1":
                check_state = 0

            messages = ["State is %s" % alarm_states[alarm_status]]

            if params["state"] != state:
                check_state = max(check_state, 1)
                messages.append(
                    "Port state Change from {} to {}".format(states[params["state"]], states[state])
                )

            return check_state, ", ".join(messages)
    return None


def parse_apc_inputs(string_table: StringTable) -> StringTable:
    return string_table


check_info["apc_inputs"] = LegacyCheckDefinition(
    parse_function=parse_apc_inputs,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.318.1.1.25.2.2.1",
        oids=["3", "4", "5", "6"],
    ),
    service_name="Input %s",
    discovery_function=inventory_apc_inputs,
    check_function=check_apc_inputs,
)
