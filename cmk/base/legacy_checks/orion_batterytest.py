#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, startswith, StringTable

check_info = {}


def discover_orion_batterytest(info):
    return [(None, {})]


def check_orion_batterytest(item, params, info):
    map_states = {
        "1": (0, "none"),
        "2": (2, "failed"),
        "3": (1, "aborted"),
        "4": (2, "load failure"),
        "5": (0, "OK"),
        "6": (1, "aborted manual"),
        "7": (1, "aborted ev ctrl charge"),
        "8": (1, "aborted inhibit ev"),
    }

    last_test_date, test_result = info[0]
    if test_result != "1":
        # dcBatteryTestResult:
        # This parameter is valid only if there is a test result available.
        state, state_readable = map_states.get(test_result, (3, "unknown[%s]" % test_result))
        infotext = f"Last performed: {last_test_date}, Result: {state_readable}"
        return state, infotext
    return 0, "No test result available"


def parse_orion_batterytest(string_table: StringTable) -> StringTable | None:
    return string_table or None


check_info["orion_batterytest"] = LegacyCheckDefinition(
    name="orion_batterytest",
    parse_function=parse_orion_batterytest,
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.20246"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.20246.2.3.1.1.1.2.5.2.2",
        oids=["1", "2"],
    ),
    service_name="Battery Test",
    discovery_function=discover_orion_batterytest,
    check_function=check_orion_batterytest,
)
