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
from cmk.plugins.juniper.lib import DETECT_JUNIPER_SCREENOS

Section = dict[str, str]


def discover_juniper_screenos_vpn(section: Section) -> DiscoveryResult:
    for vpn_id in section:
        yield Service(item=vpn_id)


def check_juniper_screenos_vpn(item: str, section: Section) -> CheckResult:
    if item not in section:
        return
    vpn_status = section[item]
    if vpn_status == "1":
        yield Result(state=State.OK, summary=f"VPN Status {item} is active")
    elif vpn_status == "0":
        yield Result(state=State.CRIT, summary=f"VPN Status {item} inactive")
    else:
        yield Result(state=State.WARN, summary=f"Unknown vpn status {vpn_status}")


def parse_juniper_screenos_vpn(string_table: StringTable) -> Section:
    return {line[0]: line[1] for line in string_table}


snmp_section_juniper_screenos_vpn = SimpleSNMPSection(
    name="juniper_screenos_vpn",
    parse_function=parse_juniper_screenos_vpn,
    detect=DETECT_JUNIPER_SCREENOS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3224.4.1.1.1",
        oids=["4", "23"],
    ),
)

check_plugin_juniper_screenos_vpn = CheckPlugin(
    name="juniper_screenos_vpn",
    service_name="VPN %s",
    discovery_function=discover_juniper_screenos_vpn,
    check_function=check_juniper_screenos_vpn,
)
