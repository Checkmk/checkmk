#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# .1.3.6.1.4.1.232.11.1.3.0  1
# .1.3.6.1.4.1.232.11.2.14.1.1.5.0  "2009.05.18"
# .1.3.6.1.4.1.232.2.2.2.1.0  "GB8851CPPH


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import all_of, any_of, contains, exists, SNMPTree, StringTable

check_info = {}


def discover_proliant_general(info):
    if info and len(info[0]) > 1 and info[0][0]:
        yield None, {}


def check_proliant_general(_no_item, _no_params, info):
    if not info:
        return None

    map_states = {
        "1": (3, "unknown"),
        "2": (0, "OK"),
        "3": (1, "degraded"),
        "4": (2, "failed"),
    }

    status, firmware, serial_number = info[0]
    state, state_readable = map_states.get(status, (3, "unhandled[%s]" % status))
    return state, f"Status: {state_readable}, Firmware: {firmware}, S/N: {serial_number}"


def parse_hp_proliant(string_table: StringTable) -> StringTable:
    return string_table


check_info["hp_proliant"] = LegacyCheckDefinition(
    name="hp_proliant",
    parse_function=parse_hp_proliant,
    detect=any_of(
        contains(".1.3.6.1.2.1.1.2.0", "8072.3.2.10"),
        contains(".1.3.6.1.2.1.1.2.0", "232.9.4.10"),
        all_of(
            contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.311.1.1.3.1.2"),
            exists(".1.3.6.1.4.1.232.11.1.3.0"),
        ),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.232",
        oids=["11.1.3.0", "11.2.14.1.1.5.0", "2.2.2.1.0"],
    ),
    service_name="General Status",
    discovery_function=discover_proliant_general,
    check_function=check_proliant_general,
)
