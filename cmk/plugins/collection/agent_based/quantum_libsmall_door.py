#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    all_of,
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)

_Section = list[list[str]] | None


def discovery_quantum_libsmall_door(section: _Section) -> DiscoveryResult:
    yield Service(item=None, parameters=None)


def check_quantum_libsmall_door(section: _Section) -> CheckResult:
    if section is None:
        return
    match section[0][0]:
        case "1":
            yield Result(state=State.CRIT, summary="Library door open")
        case "2":
            yield Result(state=State.OK, summary="Library door closed")
        case _:
            yield Result(state=State.UNKNOWN, summary="Library door unknown")


def parse_quantum_libsmall_door(string_table: StringTable) -> _Section:
    return string_table or None


snmp_section_quantum_libsmall_status = SimpleSNMPSection(
    name="quantum_libsmall_door",
    parse_function=parse_quantum_libsmall_door,
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.8072.3.2.10"),
        contains(".1.3.6.1.4.1.3697.1.10.10.1.10.0", "Quantum Small Library Product"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3697.1.10.10.1.15.2",
        oids=["0"],
    ),
)


check_plugin_quantum_libsmall_status = CheckPlugin(
    name="quantum_libsmall_door",
    service_name="Tape library door",
    discovery_function=discovery_quantum_libsmall_door,
    check_function=check_quantum_libsmall_door,
)
