#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<emcvnx_writecache>>>
# SPA Write Cache State               Enabled
# SPB Write Cache State               Enabled


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import StringTable

check_info = {}


def inventory_emcvnx_writecache(info):
    inventory = []
    for line in info:
        if " ".join(line) == "Error: getcache command failed":
            return []
        inventory.append((line[0], None))
    return inventory


def check_emcvnx_writecache(item, params, info):
    map_state = {
        "Enabled": (0, "enabled"),
        "Disabled": (2, "disabled"),
    }
    for line in info:
        if line[0] == item:
            state, state_readable = map_state.get(line[-1], (3, "unknown"))
            return state, "State: %s" % state_readable
    return None


def parse_emcvnx_writecache(string_table: StringTable) -> StringTable:
    return string_table


check_info["emcvnx_writecache"] = LegacyCheckDefinition(
    name="emcvnx_writecache",
    parse_function=parse_emcvnx_writecache,
    service_name="Write Cache State %s",
    discovery_function=inventory_emcvnx_writecache,
    check_function=check_emcvnx_writecache,
)
