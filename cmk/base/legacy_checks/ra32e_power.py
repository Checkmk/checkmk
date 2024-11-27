#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import DiscoveryResult, Service, SNMPTree, StringTable
from cmk.plugins.lib.ra32e import DETECT_RA32E

check_info = {}


def discover_ra32e_power(section: StringTable) -> DiscoveryResult:
    if section and section[0][0]:
        yield Service()


def check_ra32e_power(item, params, info):
    power = info[0][0]

    if power == "1":
        return 0, "unit is running on AC/Utility power"
    if power == "0":
        return 1, "unit is running on battery backup power"
    return 3, "unknown status"


def parse_ra32e_power(string_table: StringTable) -> StringTable:
    return string_table


check_info["ra32e_power"] = LegacyCheckDefinition(
    name="ra32e_power",
    parse_function=parse_ra32e_power,
    detect=DETECT_RA32E,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.20916.1.8.1.1.3",
        oids=["1"],
    ),
    service_name="Power Supply",
    discovery_function=discover_ra32e_power,
    check_function=check_ra32e_power,
)
