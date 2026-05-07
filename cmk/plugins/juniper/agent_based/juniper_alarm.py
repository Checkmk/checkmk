#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.juniper.lib import DETECT_JUNIPER


@dataclass(frozen=True, kw_only=True)
class JuniperAlarm:
    state: str
    state_formatted: str


CHECK_DEFAULT_PARAMS = {
    "state_1": 3,
    "state_2": 0,
    "state_3": 1,
    "state_4": 2,
    "state_5": 0,
    "state_6": 1,
    "state_7": 2,
    "state_8": 0,
    "state_9": 1,
    "state_10": 2,
    "state_11": 0,
    "state_12": 1,
}

_STATE_MAP = {
    "state_1": "unknown or unavailable",
    "state_2": "OK, good, normally working",
    "state_3": "alarm, warning, marginally working (minor)",
    "state_4": "alert, failed, not working (major)",
    "state_5": "OK, online as an active primary",
    "state_6": "alarm, offline, not running (minor)",
    "state_7": "off-line, not running",
    "state_8": "entering state of ok, good, normally working",
    "state_9": "entering state of alarm, warning, marginally working",
    "state_10": "entering state of alert, failed, not working",
    "state_11": "entering state of ok, on-line as an active primary",
    "state_12": "entering state of off-line, not running",
}


def parse_juniper_alarm(string_table: StringTable) -> JuniperAlarm | None:
    if string_table and string_table[0] and string_table[0][0] != "1":
        return JuniperAlarm(state=string_table[0][0], state_formatted=f"state_{string_table[0][0]}")
    return None


snmp_section_juniper_alarm = SimpleSNMPSection(
    name="juniper_alarm",
    parse_function=parse_juniper_alarm,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2636.3.1.10.1",
        oids=["8"],
    ),
    detect=DETECT_JUNIPER,
)


def discover_juniper_alarm(section: JuniperAlarm) -> DiscoveryResult:
    yield Service()


def check_juniper_alarm(params: Mapping[str, int], section: JuniperAlarm) -> CheckResult:
    state_value = params.get(section.state_formatted, 3)
    summary = _STATE_MAP.get(section.state_formatted, f"unhandled alarm type '{section.state}'")
    yield Result(state=State(state_value), summary=f"Status: {summary}")


check_plugin_juniper_alarm = CheckPlugin(
    name="juniper_alarm",
    service_name="Chassis",
    discovery_function=discover_juniper_alarm,
    check_function=check_juniper_alarm,
    check_default_parameters=CHECK_DEFAULT_PARAMS,
    check_ruleset_name="juniper_alarms",
)
