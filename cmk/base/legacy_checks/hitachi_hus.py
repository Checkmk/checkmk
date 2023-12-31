#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import any_of, contains, SNMPTree
from cmk.agent_based.v2.type_defs import StringTable

# For Hitachi Unified Storage (HUS) devices which support the USPMIB
# This devices has two units: Disk Controller (DKC) and Disk Unit (DKC)

# Example output from DKC:
# .1.3.6.1.4.1.116.5.11.4.1.1.6.1.1 470849
# .1.3.6.1.4.1.116.5.11.4.1.1.6.1.2 1
# .1.3.6.1.4.1.116.5.11.4.1.1.6.1.3 1
# .1.3.6.1.4.1.116.5.11.4.1.1.6.1.4 1
# .1.3.6.1.4.1.116.5.11.4.1.1.6.1.5 1
# .1.3.6.1.4.1.116.5.11.4.1.1.6.1.6 5
# .1.3.6.1.4.1.116.5.11.4.1.1.6.1.7 1
# .1.3.6.1.4.1.116.5.11.4.1.1.6.1.8 1
# .1.3.6.1.4.1.116.5.11.4.1.1.6.1.9 1

# Example output from DKU:
# .1.3.6.1.4.1.116.5.11.4.1.1.7.1.1 470849
# .1.3.6.1.4.1.116.5.11.4.1.1.7.1.2 1
# .1.3.6.1.4.1.116.5.11.4.1.1.7.1.3 4
# .1.3.6.1.4.1.116.5.11.4.1.1.7.1.4 3
# .1.3.6.1.4.1.116.5.11.4.1.1.7.1.5 1


def parse_hitachi_hus(string_table: StringTable) -> StringTable:
    return string_table


def inventory_hitachi_hus(info):
    for line in info:
        # set dkuRaidListIndexSerialNumber as item
        yield line[0], None


def check_hitachi_hus(item, _no_params, info):
    # Maps for hitachi hus components
    hus_map_states = {
        "0": (3, "unknown"),
        "1": (0, "no error"),
        "2": (2, "acute"),
        "3": (2, "serious"),
        "4": (1, "moderate"),
        "5": (1, "service"),
    }

    ok_states = []
    warn_states = []
    crit_states = []
    unknown_states = []

    # We need to take care that the right map type is checked
    if len(info[0]) == 5:
        component = [
            "Power Supply",
            "Fan",
            "Environment",
            "Drive",
        ]
    else:
        component = [
            "Processor",
            "Internal Bus",
            "Cache",
            "Shared Memory",
            "Power Supply",
            "Battery",
            "Fan",
            "Environment",
        ]

    # Check the state of the components and add the output to the state lists
    for line in info:
        if line[0] != item:
            continue

        for what, device_state in zip(component, line[1:]):
            state, state_readable = hus_map_states[device_state]
            if state == 0:
                ok_states.append(f"{what}: {state_readable}")
            if state == 1:
                warn_states.append(f"{what}: {state_readable}")
            if state == 2:
                crit_states.append(f"{what}: {state_readable}")
            if state == 3:
                unknown_states.append(f"{what}: {state_readable}")

        for state, states, text in [
            (0, ok_states, "OK"),
            (3, unknown_states, "UNKNOWN"),
            (1, warn_states, "WARN"),
            (2, crit_states, "CRIT"),
        ]:
            if states:
                yield state, "{}: {}".format(text, ", ".join(states))


check_info["hitachi_hus_dkc"] = LegacyCheckDefinition(
    parse_function=parse_hitachi_hus,
    detect=any_of(
        contains(".1.3.6.1.2.1.1.1.0", "hm700"),
        contains(".1.3.6.1.2.1.1.1.0", "hm800"),
        contains(".1.3.6.1.2.1.1.1.0", "hm850"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.116.5.11.4.1.1.6.1",
        oids=["1", "2", "3", "4", "5", "6", "7", "8", "9"],
    ),
    service_name="HUS DKC Chassis %s",
    discovery_function=inventory_hitachi_hus,
    check_function=check_hitachi_hus,
)


check_info["hitachi_hus_dku"] = LegacyCheckDefinition(
    parse_function=parse_hitachi_hus,
    detect=any_of(
        contains(".1.3.6.1.2.1.1.1.0", "hm700"),
        contains(".1.3.6.1.2.1.1.1.0", "hm800"),
        contains(".1.3.6.1.2.1.1.1.0", "hm850"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.116.5.11.4.1.1.7.1",
        oids=["1", "2", "3", "4", "5"],
    ),
    service_name="HUS DKU Chassis %s",
    discovery_function=inventory_hitachi_hus,
    check_function=check_hitachi_hus,
)
