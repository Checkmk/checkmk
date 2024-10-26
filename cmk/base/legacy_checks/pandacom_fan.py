#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# .1.3.6.1.4.1.3652.3.2.3.1.2.1 3 --> SPEEDCARRIER-MIB::nmFanGroupStatus.1
# .1.3.6.1.4.1.3652.3.2.3.1.2.2 3 --> SPEEDCARRIER-MIB::nmFanGroupStatus.2
# .1.3.6.1.4.1.3652.3.2.3.1.2.3 3 --> SPEEDCARRIER-MIB::nmFanGroupStatus.3
# .1.3.6.1.4.1.3652.3.2.3.1.2.4 3 --> SPEEDCARRIER-MIB::nmFanGroupStatus.4
# .1.3.6.1.4.1.3652.3.2.3.1.2.5 3 --> SPEEDCARRIER-MIB::nmFanGroupStatus.5
# .1.3.6.1.4.1.3652.3.2.3.1.2.6 3 --> SPEEDCARRIER-MIB::nmFanGroupStatus.6
# .1.3.6.1.4.1.3652.3.2.3.1.2.7 3 --> SPEEDCARRIER-MIB::nmFanGroupStatus.7
# .1.3.6.1.4.1.3652.3.2.3.1.2.8 3 --> SPEEDCARRIER-MIB::nmFanGroupStatus.8
# .1.3.6.1.4.1.3652.3.2.3.1.2.9 3 --> SPEEDCARRIER-MIB::nmFanGroupStatus.9
# .1.3.6.1.4.1.3652.3.2.3.1.2.10 3 --> SPEEDCARRIER-MIB::nmFanGroupStatus.10


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.pandacom import DETECT_PANDACOM

check_info = {}


def inventory_pandacom_fan(info):
    return [(fan_nr, None) for fan_nr, fan_state in info if fan_state not in ["0", "5"]]


def check_pandacom_fan(item, params, info):
    map_fan_state = {
        "0": (3, "not available"),
        "1": (0, "on"),
        "2": (2, "off"),
        "3": (0, "pass"),
        "4": (2, "fail"),
        "5": (3, "not installed"),
        "6": (0, "auto"),
    }
    for fan_nr, fan_state in info:
        if fan_nr == item:
            state, state_readable = map_fan_state[fan_state]
            return state, "Operational status: %s" % state_readable
    return None


def parse_pandacom_fan(string_table: StringTable) -> StringTable:
    return string_table


check_info["pandacom_fan"] = LegacyCheckDefinition(
    name="pandacom_fan",
    parse_function=parse_pandacom_fan,
    detect=DETECT_PANDACOM,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3652.3.2.3.1",
        oids=["1", "2"],
    ),
    service_name="Fan %s",
    discovery_function=inventory_pandacom_fan,
    check_function=check_pandacom_fan,
)
