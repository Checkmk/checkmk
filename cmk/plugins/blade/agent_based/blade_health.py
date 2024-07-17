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

from .detection import DETECT_BLADE

# Example excerpt from SNMP data:
# .1.3.6.1.4.1.2.3.51.2.2.7.1.0  255
# .1.3.6.1.4.1.2.3.51.2.2.7.2.1.1.1  1
# .1.3.6.1.4.1.2.3.51.2.2.7.2.1.2.1  "Good"
# .1.3.6.1.4.1.2.3.51.2.2.7.2.1.3.1  "No critical or warning events"
# .1.3.6.1.4.1.2.3.51.2.2.7.2.1.4.1  "No timestamp"


def inventory_blade_health(section: StringTable) -> DiscoveryResult:
    if len(section) == 1:
        yield Service()


def check_blade_health(section: StringTable) -> CheckResult:
    state = section[0][0]
    descr = ": " + ", ".join([line[1] for line in section if len(line) > 1])

    if state == "255":
        yield Result(state=State.OK, summary="State is good")
        return
    if state == "2":
        yield Result(state=State.WARN, summary="State is degraded (non critical)" + descr)
        return
    if state == "4":
        yield Result(state=State.WARN, summary="State is degraded (system level)" + descr)
        return
    if state == "0":
        yield Result(state=State.CRIT, summary="State is critical!" + descr)
        return
    yield Result(state=State.UNKNOWN, summary=f"Undefined state code {state}{descr}")
    return


def parse_blade_health(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_blade_health = SimpleSNMPSection(
    name="blade_health",
    detect=DETECT_BLADE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2.3.51.2.2.7",
        oids=["1.0", "2.1.3.1"],
    ),
    parse_function=parse_blade_health,
)
check_plugin_blade_health = CheckPlugin(
    name="blade_health",
    service_name="Summary health state",
    discovery_function=inventory_blade_health,
    check_function=check_blade_health,
)
