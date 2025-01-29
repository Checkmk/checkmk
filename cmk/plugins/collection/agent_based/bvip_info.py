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
from cmk.plugins.lib.bvip import DETECT_BVIP


def inventory_bvip_info(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


def check_bvip_info(section: StringTable) -> CheckResult:
    unit_name, unit_id = section[0]
    if unit_name == unit_id:
        yield Result(state=State.OK, summary="Unit Name/ID: " + unit_name)
        return
    yield Result(state=State.OK, summary=f"Unit Name: {unit_name}, Unit ID: {unit_id}")
    return


def parse_bvip_info(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_bvip_info = SimpleSNMPSection(
    name="bvip_info",
    detect=DETECT_BVIP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3967.1.1.1",
        oids=["1", "2"],
    ),
    parse_function=parse_bvip_info,
)
check_plugin_bvip_info = CheckPlugin(
    name="bvip_info",
    service_name="System Info",
    discovery_function=inventory_bvip_info,
    check_function=check_bvip_info,
)
