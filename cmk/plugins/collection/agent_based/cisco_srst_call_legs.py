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
    equals,
    Metric,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)


def inventory_cisco_srst_call_legs(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_cisco_srst_call_legs(section: StringTable) -> CheckResult:
    call_legs = int(section[0][0])
    yield Result(
        state=State.OK,
        summary="%d call legs routed through the Cisco device since going active" % call_legs,
    )
    yield Metric("call_legs", call_legs)


def parse_cisco_srst_call_legs(string_table: StringTable) -> StringTable | None:
    return string_table or None


snmp_section_cisco_srst_call_legs = SimpleSNMPSection(
    name="cisco_srst_call_legs",
    detect=all_of(
        contains(".1.3.6.1.2.1.1.1.0", "cisco"), equals(".1.3.6.1.4.1.9.9.441.1.2.1.0", "1")
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.441.1.3",
        oids=["3"],
    ),
    parse_function=parse_cisco_srst_call_legs,
)


check_plugin_cisco_srst_call_legs = CheckPlugin(
    name="cisco_srst_call_legs",
    service_name="SRST Call Legs",
    discovery_function=inventory_cisco_srst_call_legs,
    check_function=check_cisco_srst_call_legs,
)
