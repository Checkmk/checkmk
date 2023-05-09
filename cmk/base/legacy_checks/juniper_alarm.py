#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# .1.3.6.1.4.1.2636.3.1.10.1.8.3.1.1.0.0 1 --> JUNIPER-MIB::jnxLEDState.jnxContentsTable.1.1.0.0


from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.juniper import DETECT_JUNIPER


def inventory_juniper_alarm(info):
    if len(info) > 0 and info[0][0] != "1":
        return [(None, None)]
    return []


def check_juniper_alarm(item, params, info):
    map_alarm = {
        "1": (3, "unknown or unavailable"),
        "2": (0, "OK, good, normally working"),
        "3": (1, "alarm, warning, marginally working (minor)"),
        "4": (2, "alert, failed, not working (major)"),
        "5": (0, "OK, online as an active primary"),
        "6": (1, "alarm, offline, not running (minor)"),
    }
    alarm_state = info[0][0]
    state, state_readable = map_alarm.get(
        alarm_state, (3, "unhandled alarm type '%s'" % alarm_state)
    )
    return state, "Status: %s" % state_readable


check_info["juniper_alarm"] = {
    "detect": DETECT_JUNIPER,
    "discovery_function": inventory_juniper_alarm,
    "check_function": check_juniper_alarm,
    "service_name": "Chassis",
    # Use utils.juniper.DETECT when migrating
    "fetch": SNMPTree(
        base=".1.3.6.1.4.1.2636.3.1.10.1",
        oids=["8"],
    ),
}
