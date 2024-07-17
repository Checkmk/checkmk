#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    any_of,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    equals,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)


def inventory_bintec_info(section: StringTable) -> DiscoveryResult:
    if section and section[0]:
        yield Service()


def check_bintec_info(section: StringTable) -> CheckResult:
    if len(section[0]) < 2:
        yield Result(state=State.UNKNOWN, summary="No data retrieved")
        return
    sw_version, serial = section[0]
    yield Result(state=State.OK, summary=f"Serial: {serial}, Software: {sw_version}")
    return


# 1.3.6.1.4.1.272.4.1.26.0 SW Version
# 1.3.6.1.4.1.272.4.1.31.0 S/N

# This check works on all SNMP hosts


def parse_bintec_info(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_bintec_info = SimpleSNMPSection(
    name="bintec_info",
    detect=any_of(
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.272.4.200.83.88.67.66.0.0"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.272.4.158.82.78.66.48.0.0"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.272.4.1",
        oids=["26.0", "31.0"],
    ),
    parse_function=parse_bintec_info,
)
check_plugin_bintec_info = CheckPlugin(
    name="bintec_info",
    service_name="Bintec Info",
    discovery_function=inventory_bintec_info,
    check_function=check_bintec_info,
)
