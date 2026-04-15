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


def discover_pfsense_status(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


def check_pfsense_status(section: StringTable) -> CheckResult:
    match section[0][0]:
        case "1":
            yield Result(state=State.OK, summary="Running")
        case "2":
            yield Result(state=State.CRIT, summary="Not running")
        case other:
            yield Result(state=State.UNKNOWN, summary=f"Unknown status value: {other!r}")


def parse_pfsense_status(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_pfsense_status = SimpleSNMPSection(
    name="pfsense_status",
    detect=contains(".1.3.6.1.2.1.1.1.0", "pfsense"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12325.1.200.1.1",
        oids=["1"],
    ),
    parse_function=parse_pfsense_status,
)


check_plugin_pfsense_status = CheckPlugin(
    name="pfsense_status",
    service_name="pfSense Status",
    discovery_function=discover_pfsense_status,
    check_function=check_pfsense_status,
)
