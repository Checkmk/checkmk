#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.juniper import DETECT_JUNIPER_SCREENOS


def inventory_juniper_screenos_vpn(info):
    return [(line[0], None) for line in info]


def check_juniper_screenos_vpn(item, params, info):
    for vpn_id, vpn_status in info:
        if vpn_id == item:
            if vpn_status == "1":
                return (0, "VPN Status %s is active" % vpn_id)
            if vpn_status == "0":
                return (2, "VPN Status %s inactive" % vpn_id)
            return (1, "Unknown vpn status %s" % vpn_status)
    return (2, "VPN name not found in SNMP data")


check_info["juniper_screenos_vpn"] = {
    "detect": DETECT_JUNIPER_SCREENOS,
    "check_function": check_juniper_screenos_vpn,
    "discovery_function": inventory_juniper_screenos_vpn,
    "service_name": "VPN %s",
    "fetch": SNMPTree(
        base=".1.3.6.1.4.1.3224.4.1.1.1",
        oids=["4", "23"],
    ),
}
