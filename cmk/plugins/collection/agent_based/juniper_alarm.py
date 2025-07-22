#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
from cmk.plugins.lib.juniper import DETECT_JUNIPER


@dataclass(frozen=True, kw_only=True)
class JuniperAlarm:
    state: str


_STATE_MAP = {
    "1": Result(state=State.UNKNOWN, summary="Status: unknown or unavailable"),
    "2": Result(state=State.OK, summary="Status: OK, good, normally working"),
    "3": Result(state=State.WARN, summary="Status: alarm, warning, marginally working (minor)"),
    "4": Result(state=State.CRIT, summary="Status: alert, failed, not working (major)"),
    "5": Result(state=State.OK, summary="Status: OK, online as an active primary"),
    "6": Result(state=State.WARN, summary="Status: alarm, offline, not running (minor)"),
    "7": Result(state=State.CRIT, summary="Status: off-line, not running"),
    "8": Result(state=State.OK, summary="Status: entering state of ok, good, normally working"),
    "9": Result(
        state=State.WARN, summary="Status: entering state of alarm, warning, marginally working"
    ),
    "10": Result(state=State.CRIT, summary="Status: entering state of alert, failed, not working"),
    "11": Result(
        state=State.OK, summary="Status: entering state of ok, on-line as an active primary"
    ),
    "12": Result(state=State.WARN, summary="Status: entering state of off-line, not running"),
}


def parse_juniper_alarm(string_table: StringTable) -> JuniperAlarm | None:
    if string_table and string_table[0] and string_table[0][0] != "1":
        return JuniperAlarm(state=string_table[0][0])
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


def check_juniper_alarm(section: JuniperAlarm) -> CheckResult:
    yield _STATE_MAP.get(
        section.state,
        Result(state=State.UNKNOWN, summary="Status: unhandled alarm type '%s'" % section.state),
    )


check_plugin_juniper_alarm = CheckPlugin(
    name="juniper_alarm",
    service_name="Chassis",
    discovery_function=discover_juniper_alarm,
    check_function=check_juniper_alarm,
)
