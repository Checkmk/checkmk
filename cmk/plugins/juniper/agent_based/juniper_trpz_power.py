#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

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
from cmk.plugins.juniper.lib import DETECT_JUNIPER_TRPZ

Section = Mapping[str, int]


def discover_juniper_trpz_power(section: Section) -> DiscoveryResult:
    for line in section:
        yield Service(item=line)


def check_juniper_trpz_power(item: str, section: Section) -> CheckResult:
    if item not in section:
        return
    states = {
        1: "other",
        2: "unknown",
        3: "ac-failed",
        4: "dc-failed",
        5: "ac-ok-dc-ok",
    }
    state = section[item]

    message = f"Current state: {states[state]}"
    if state in [2, 3, 4]:
        yield Result(state=State.CRIT, summary=message)
    if state == 1:
        yield Result(state=State.WARN, summary=message)
    yield Result(state=State.OK, summary=message)


def parse_juniper_trpz_power(string_table: StringTable) -> Section:
    return {line[0]: int(line[1]) for line in string_table}


snmp_section_juniper_trpz_power = SimpleSNMPSection(
    name="juniper_trpz_power",
    parse_function=parse_juniper_trpz_power,
    detect=DETECT_JUNIPER_TRPZ,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.14525.4.8.1.1.13.1.2.1",
        oids=["3", "2"],
    ),
)

check_plugin_juniper_trpz_power = CheckPlugin(
    name="juniper_trpz_power",
    service_name="PSU %s",
    discovery_function=discover_juniper_trpz_power,
    check_function=check_juniper_trpz_power,
)
