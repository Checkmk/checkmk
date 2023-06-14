#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree, startswith


def inventory_orion_batterytest(info):
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
        infotext = "Last performed: %s, Result: %s" % (last_test_date, state_readable)
        return state, infotext
    return 0, "No test result available"


check_info["orion_batterytest"] = LegacyCheckDefinition(
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.20246"),
    discovery_function=inventory_orion_batterytest,
    check_function=check_orion_batterytest,
    service_name="Battery Test",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.20246.2.3.1.1.1.2.5.2.2",
        oids=["1", "2"],
    ),
)
