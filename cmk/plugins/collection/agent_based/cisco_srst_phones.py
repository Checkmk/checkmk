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


def inventory_cisco_srst_phones(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_cisco_srst_phones(section: StringTable) -> CheckResult:
    phones = int(section[0][0])
    yield Result(
        state=State.OK,
        summary="%d phones registered" % phones,
    )
    yield Metric("registered_phones", phones)


def parse_cisco_srst_phones(string_table: StringTable) -> StringTable | None:
    return string_table or None


snmp_section_cisco_srst_phones = SimpleSNMPSection(
    name="cisco_srst_phones",
    detect=all_of(
        contains(".1.3.6.1.2.1.1.1.0", "cisco"), equals(".1.3.6.1.4.1.9.9.441.1.2.1.0", "1")
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.441.1.3",
        oids=["2"],
    ),
    parse_function=parse_cisco_srst_phones,
)
check_plugin_cisco_srst_phones = CheckPlugin(
    name="cisco_srst_phones",
    service_name="SRST Phones",
    discovery_function=inventory_cisco_srst_phones,
    check_function=check_cisco_srst_phones,
)
