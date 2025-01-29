#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)


def inventory_bdtms_tape_info(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_bdtms_tape_info(section: StringTable) -> CheckResult:
    for name, value in zip(
        ["Vendor", "Product ID", "Serial Number", "Software Revision"], section[0]
    ):
        yield Result(state=State.OK, summary=f"{name}: {value}")


def parse_bdtms_tape_info(string_table: StringTable) -> StringTable | None:
    return string_table or None


snmp_section_bdtms_tape_info = SimpleSNMPSection(
    name="bdtms_tape_info",
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.20884.77.83.1"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.20884.1",
        oids=["1", "2", "3", "4"],
    ),
    parse_function=parse_bdtms_tape_info,
)
check_plugin_bdtms_tape_info = CheckPlugin(
    name="bdtms_tape_info",
    service_name="Tape Library Info",
    discovery_function=inventory_bdtms_tape_info,
    check_function=check_bdtms_tape_info,
)
