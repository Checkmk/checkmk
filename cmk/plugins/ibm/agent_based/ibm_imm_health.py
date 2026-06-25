#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
from cmk.plugins.ibm.lib import DETECT_IBM_IMM


def discover_ibm_imm_health(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


def check_ibm_imm_health(section: StringTable) -> CheckResult:
    if not section or not section[0]:
        yield Result(state=State.UNKNOWN, summary="Health info not found in SNMP data")
        return

    num_alerts = int((len(section) - 1) / 3)
    infotext = ""
    for i in range(num_alerts):
        state = section[num_alerts + 1 + i][0]
        text = section[num_alerts * 2 + 1 + i][0]
        if infotext != "":
            infotext += ", "
        infotext += f"{text}({state})"

    state = section[0][0]
    if state == "255":
        yield Result(state=State.OK, summary="no problem found")
        return
    if state == "0":
        yield Result(
            state=State.CRIT, summary=infotext + " - manual log clearing needed to recover state"
        )
        return
    if state == "2":
        yield Result(state=State.CRIT, summary=infotext)
        return
    if state == "4":
        yield Result(state=State.WARN, summary=infotext)
        return
    yield Result(state=State.UNKNOWN, summary=infotext)
    return


def parse_ibm_imm_health(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_ibm_imm_health = SimpleSNMPSection(
    name="ibm_imm_health",
    detect=DETECT_IBM_IMM,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2.3.51.3.1",
        oids=["4"],
    ),
    parse_function=parse_ibm_imm_health,
)


check_plugin_ibm_imm_health = CheckPlugin(
    name="ibm_imm_health",
    service_name="System health",
    discovery_function=discover_ibm_imm_health,
    check_function=check_ibm_imm_health,
)
