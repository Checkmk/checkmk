#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# .1.3.6.1.4.1.12148.9.2.2.0 1 --> ELTEK-DISTRIBUTED-MIB::systemOperationalStatus.0


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.eltek import DETECT_ELTEK

check_info = {}


def inventory_eltek_systemstatus(info):
    return [(None, None)]


def check_eltek_systemstatus(_no_item, _no_params, info):
    map_state = {
        "0": (2, "float, voltage regulated"),
        "1": (0, "float, temperature comp. regulated"),
        "2": (2, "battery boost"),
        "3": (2, "battery test"),
    }
    state, state_readable = map_state[info[0][0]]
    return state, "Operational status: %s" % state_readable


def parse_eltek_systemstatus(string_table: StringTable) -> StringTable | None:
    return string_table or None


check_info["eltek_systemstatus"] = LegacyCheckDefinition(
    name="eltek_systemstatus",
    parse_function=parse_eltek_systemstatus,
    detect=DETECT_ELTEK,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12148.9.2",
        oids=["2"],
    ),
    service_name="System Status",
    discovery_function=inventory_eltek_systemstatus,
    check_function=check_eltek_systemstatus,
)
