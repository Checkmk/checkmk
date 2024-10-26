#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import DiscoveryResult, Service, SNMPTree, StringTable
from cmk.plugins.lib.viprinet import DETECT_VIPRINET

check_info = {}


def check_viprinet_power(_no_item, params, info):
    power_map = {
        "0": "no failure",
        "1": "a single PSU is out of order",
    }
    power_info = power_map.get(info[0][0])
    if power_info:
        return (0, power_info)
    return (3, "Invalid power status")


def parse_viprinet_power(string_table: StringTable) -> StringTable:
    return string_table


def discover_viprinet_power(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


check_info["viprinet_power"] = LegacyCheckDefinition(
    name="viprinet_power",
    parse_function=parse_viprinet_power,
    detect=DETECT_VIPRINET,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.35424.1.2",
        oids=["5"],
    ),
    service_name="Power-Supply",
    discovery_function=discover_viprinet_power,
    check_function=check_viprinet_power,
)
