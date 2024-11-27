#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.genua import DETECT_GENUA

check_info = {}

# .1.3.6.1.4.1.3717.2.1.3.1.1.1 1
# .1.3.6.1.4.1.3717.2.1.3.1.1.2 2
# .1.3.6.1.4.1.3717.2.1.3.1.1.3 3
# .1.3.6.1.4.1.3717.2.1.3.1.1.4 4
# .1.3.6.1.4.1.3717.2.1.3.1.2.1 gc2.momatec.de
# .1.3.6.1.4.1.3717.2.1.3.1.2.2 gc1-bsge.vrznrw.de
# .1.3.6.1.4.1.3717.2.1.3.1.2.3 gc1-bochum.vrznrw.de
# .1.3.6.1.4.1.3717.2.1.3.1.2.4 gc1-hamm.vrznrw.de
# .1.3.6.1.4.1.3717.2.1.3.1.3.1
# .1.3.6.1.4.1.3717.2.1.3.1.3.2 10.99.15.250
# .1.3.6.1.4.1.3717.2.1.3.1.3.3 10.99.13.250
# .1.3.6.1.4.1.3717.2.1.3.1.3.4 10.99.14.250
# .1.3.6.1.4.1.3717.2.1.3.1.4.1 172.30.230.24/32
# .1.3.6.1.4.1.3717.2.1.3.1.4.2 172.30.230.24/32
# .1.3.6.1.4.1.3717.2.1.3.1.4.3 172.30.230.24/32
# .1.3.6.1.4.1.3717.2.1.3.1.4.4 172.30.230.24/32
# .1.3.6.1.4.1.3717.2.1.3.1.5.1 192.168.100.0/24
# .1.3.6.1.4.1.3717.2.1.3.1.5.2 10.100.15.0/24
# .1.3.6.1.4.1.3717.2.1.3.1.5.3 10.100.13.0/24
# .1.3.6.1.4.1.3717.2.1.3.1.5.4 10.100.14.0/24
# .1.3.6.1.4.1.3717.2.1.3.1.6.1 2
# .1.3.6.1.4.1.3717.2.1.3.1.6.2 2
# .1.3.6.1.4.1.3717.2.1.3.1.6.3 2
# .1.3.6.1.4.1.3717.2.1.3.1.6.4 2


def inventory_genua_vpn(info):
    return [(line[0], None) for line in info]


def check_genua_vpn(item, params, info):
    for vpn_id, hostname_opposite, ip_opposite, vpn_private, vpn_remote, vpn_state in info:
        if vpn_id == item:
            ip_info = ""
            if ip_opposite:
                ip_info += " (%s)" % ip_opposite

            infotext = f"Hostname: {hostname_opposite}{ip_info}, VPN private: {vpn_private}, VPN remote: {vpn_remote}"

            if vpn_state == "2":
                return 0, "Connected, %s" % infotext
            return 2, "Disconnected, %s" % infotext
    return None


def parse_genua_vpn(string_table: StringTable) -> StringTable:
    return string_table


check_info["genua_vpn"] = LegacyCheckDefinition(
    name="genua_vpn",
    parse_function=parse_genua_vpn,
    detect=DETECT_GENUA,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3717.2.1.3.1",
        oids=["1", "2", "3", "4", "5", "6"],
    ),
    service_name="VPN %s",
    discovery_function=inventory_genua_vpn,
    check_function=check_genua_vpn,
)
