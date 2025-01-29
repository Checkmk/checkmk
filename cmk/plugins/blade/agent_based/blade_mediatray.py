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


def inventory_blade_mediatray(section: StringTable) -> DiscoveryResult:
    if len(section) == 1 and section[0][0] == "1":
        yield Service()


def check_blade_mediatray(section: StringTable) -> CheckResult:
    if len(section) < 1:
        yield Result(state=State.UNKNOWN, summary="no information about media tray in SNMP output")
        return
    present = section[0][0]
    communicating = section[0][1]
    if present != "1":
        yield Result(state=State.CRIT, summary="media tray not present")
        return
    if communicating != "1":
        yield Result(state=State.CRIT, summary="media tray not communicating")
        return
    yield Result(state=State.OK, summary="media tray present and communicating")
    return


def parse_blade_mediatray(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_blade_mediatray = SimpleSNMPSection(
    name="blade_mediatray",
    detect=DETECT_BLADE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2.3.51.2.2.5.2",
        oids=["74", "75"],
    ),
    parse_function=parse_blade_mediatray,
)
check_plugin_blade_mediatray = CheckPlugin(
    name="blade_mediatray",
    service_name="Media tray",
    discovery_function=inventory_blade_mediatray,
    check_function=check_blade_mediatray,
)
