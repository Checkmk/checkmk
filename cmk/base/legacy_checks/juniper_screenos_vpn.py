#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.juniper.lib import DETECT_JUNIPER_SCREENOS

check_info = {}


def discover_juniper_screenos_vpn(info: StringTable) -> Iterable[tuple[str, None]]:
    return [(line[0], None) for line in info]


def check_juniper_screenos_vpn(item: str, params: None, info: StringTable) -> tuple[int, str]:
    for vpn_id, vpn_status in info:
        if vpn_id == item:
            if vpn_status == "1":
                return (0, "VPN Status %s is active" % vpn_id)
            if vpn_status == "0":
                return (2, "VPN Status %s inactive" % vpn_id)
            return (1, "Unknown vpn status %s" % vpn_status)
    return (2, "VPN name not found in SNMP data")


def parse_juniper_screenos_vpn(string_table: StringTable) -> StringTable:
    return string_table


check_info["juniper_screenos_vpn"] = LegacyCheckDefinition(
    name="juniper_screenos_vpn",
    parse_function=parse_juniper_screenos_vpn,
    detect=DETECT_JUNIPER_SCREENOS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3224.4.1.1.1",
        oids=["4", "23"],
    ),
    service_name="VPN %s",
    discovery_function=discover_juniper_screenos_vpn,
    check_function=check_juniper_screenos_vpn,
)
