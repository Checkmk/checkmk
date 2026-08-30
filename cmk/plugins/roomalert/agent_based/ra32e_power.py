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
from cmk.plugins.roomalert.lib import DETECT_RA32E


def discover_ra32e_power(section: StringTable) -> DiscoveryResult:
    if section and section[0][0]:
        yield Service()


def check_ra32e_power(section: StringTable) -> CheckResult:
    power = section[0][0]

    if power == "1":
        yield Result(state=State.OK, summary="unit is running on AC/Utility power")
    elif power == "0":
        yield Result(state=State.WARN, summary="unit is running on battery backup power")
    else:
        yield Result(state=State.UNKNOWN, summary="unknown status")


def parse_ra32e_power(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_ra32e_power = SimpleSNMPSection(
    name="ra32e_power",
    parse_function=parse_ra32e_power,
    detect=DETECT_RA32E,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.20916.1.8.1.1.3",
        oids=["1"],
    ),
)


check_plugin_ra32e_power = CheckPlugin(
    name="ra32e_power",
    service_name="Power Supply",
    discovery_function=discover_ra32e_power,
    check_function=check_ra32e_power,
)
