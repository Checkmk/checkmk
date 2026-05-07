#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)

_OPER_STATE_MAP = {
    1: "running normally",
    2: "not running",
    3: "currently starting",
    4: "currently stopping",
    5: "fault",
}

_SYS_LEAP_STATE_MAP = {
    0: "no Warning",
    1: "add second",
    10: "subtract second",
    11: "Alarm",
}


def parse_bluecat_ntp(string_table: StringTable) -> StringTable | None:
    return string_table or None


def discover_bluecat_ntp(section: StringTable) -> DiscoveryResult:
    if section[0][0] != "NULL":
        yield Service()


def check_bluecat_ntp(
    params: Mapping[str, Any],
    section: StringTable,
) -> CheckResult:
    oper_state, sys_leap, stratum = map(int, section[0])

    state = State.OK
    if oper_state in params["oper_states"]["warning"]:
        state = State.WARN
    elif oper_state in params["oper_states"]["critical"]:
        state = State.CRIT
    yield Result(state=state, summary=f"Process is {_OPER_STATE_MAP[oper_state]}")

    state = State.OK
    if sys_leap == 11:
        state = State.CRIT
    elif sys_leap in [1, 10]:
        state = State.WARN
    yield Result(state=state, summary=f"Sys Leap: {_SYS_LEAP_STATE_MAP[sys_leap]}")

    warn, crit = params["stratum"]
    state = State.OK
    if stratum >= crit:
        state = State.CRIT
    elif stratum >= warn:
        state = State.WARN
    yield Result(state=state, summary=f"Stratum: {stratum}")


snmp_section_bluecat_ntp = SimpleSNMPSection(
    name="bluecat_ntp",
    parse_function=parse_bluecat_ntp,
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.13315"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.13315.3.1.4.2",
        oids=["1.1", "2.1", "2.2"],
    ),
)

check_plugin_bluecat_ntp = CheckPlugin(
    name="bluecat_ntp",
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
