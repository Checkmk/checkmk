#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import all_of, contains, not_exists, SNMPTree, StringTable


def inventory_cisco_temp(info):
    for name, state in info:
        if state != "5":
            yield name, None


def check_cisco_temp(item, _no_params, info):
    map_states = {
        "1": (0, "OK"),
        "2": (1, "warning"),
        "3": (2, "critical"),
        "4": (2, "shutdown"),
        "5": (3, "not present"),
        "6": (3, "value out of range"),
    }

    for name, dev_state in info:
        if name == item:
            state, state_readable = map_states.get(dev_state, (3, "unknown[%s]" % dev_state))
            return state, "Status: %s" % state_readable

    return 3, "sensor not found in SNMP output"


def parse_cisco_temp(string_table: StringTable) -> StringTable:
    return string_table


check_info["cisco_temp"] = LegacyCheckDefinition(
    parse_function=parse_cisco_temp,
    detect=all_of(
        contains(".1.3.6.1.2.1.1.1.0", "cisco"), not_exists(".1.3.6.1.4.1.9.9.13.1.3.1.3.*")
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.13.1.3.1",
        oids=["2", "6"],
    ),
    service_name="Temperature %s",
    discovery_function=inventory_cisco_temp,
    check_function=check_cisco_temp,
)
