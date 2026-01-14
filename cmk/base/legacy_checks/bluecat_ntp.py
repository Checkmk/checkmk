#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, startswith, StringTable

check_info = {}


def discover_bluecat_ntp(info):
    if len(info) > 0 and info[0][0] != "NULL":
        return [(None, None)]
    return []


def check_bluecat_ntp(item, params, info):
    oper_state, sys_leap, stratum = map(int, info[0])
    oper_states = {
        1: "running normally",
        2: "not running",
        3: "currently starting",
        4: "currently stopping",
        5: "fault",
    }

    state = 0
    if oper_state in params["oper_states"]["warning"]:
        state = 1
    elif oper_state in params["oper_states"]["critical"]:
        state = 2
    yield state, "Process is %s" % oper_states[oper_state]

    sys_leap_states = {0: "no Warning", 1: "add second", 10: "subtract second", 11: "Alarm"}
    state = 0
    if sys_leap == 11:
        state = 2
    elif sys_leap in [1, 10]:
        state = 1
    yield state, "Sys Leap: %s" % sys_leap_states[sys_leap]

    warn, crit = params["stratum"]
    state = 0
    if stratum >= crit:
        state = 2
    elif stratum >= warn:
        state = 1
    yield state, "Stratum: %s" % stratum


def parse_bluecat_ntp(string_table: StringTable) -> StringTable:
    return string_table


check_info["bluecat_ntp"] = LegacyCheckDefinition(
    name="bluecat_ntp",
    parse_function=parse_bluecat_ntp,
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.13315"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.13315.3.1.4.2",
        oids=["1.1", "2.1", "2.2"],
    ),
    service_name="NTP",
    discovery_function=discover_bluecat_ntp,
    check_function=check_bluecat_ntp,
    check_ruleset_name="bluecat_ntp",
    check_default_parameters={
        "oper_states": {
            "warning": [2, 3, 4],
            "critical": [5],
        },
        "stratum": (8, 10),
    },
)
