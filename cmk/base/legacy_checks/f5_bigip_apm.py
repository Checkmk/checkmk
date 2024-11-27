#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_legacy_includes.f5_bigip import DETECT

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import DiscoveryResult, Service, SNMPTree, StringTable

check_info = {}


def discover_f5_bigip_apm(section: StringTable) -> DiscoveryResult:
    if section and section[0][0]:
        yield Service()


def check_f5_bigip_apm(item, _no_params, info):
    count = info[0][0]
    perfdata = [("connections_ssl_vpn", int(count), None, None, 0, None)]
    return 0, "Connections: %s" % count, perfdata


def parse_f5_bigip_apm(string_table: StringTable) -> StringTable:
    return string_table


check_info["f5_bigip_apm"] = LegacyCheckDefinition(
    name="f5_bigip_apm",
    parse_function=parse_f5_bigip_apm,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3375.2.6.1.5.3",
        oids=["0"],
    ),
    service_name="SSL/VPN Connections",
    discovery_function=discover_f5_bigip_apm,
    check_function=check_f5_bigip_apm,
)
