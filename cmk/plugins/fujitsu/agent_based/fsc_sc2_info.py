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
from cmk.plugins.fujitsu.lib import DETECT_FSC_SC2

# .1.3.6.1.4.1.231.2.10.2.2.10.2.3.1.5.1 "PRIMERGY RX300 S8"
# .1.3.6.1.4.1.231.2.10.2.2.10.2.3.1.7.1 "--"
# .1.3.6.1.4.1.231.2.10.2.2.10.4.1.1.11.1 "V4.6.5.4 R1.6.0 for D2939-B1x"


def parse_fsc_sc2_info(string_table: StringTable) -> StringTable:
    return string_table


def discover_fsc_sc2_info(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


def check_fsc_sc2_info(section: StringTable) -> CheckResult:
    if section:
        model, serial_number, bios_version = section[0]
        yield Result(
            state=State.OK,
            summary=f"Model: {model}, Serial Number: {serial_number}, BIOS Version: {bios_version}",
        )


snmp_section_fsc_sc2_info = SimpleSNMPSection(
    name="fsc_sc2_info",
    parse_function=parse_fsc_sc2_info,
    detect=DETECT_FSC_SC2,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.231.2.10.2.2.10",
        oids=["2.3.1.5.1", "2.3.1.7.1", "4.1.1.11.1"],
    ),
)


check_plugin_fsc_sc2_info = CheckPlugin(
    name="fsc_sc2_info",
    service_name="Server Info",
    discovery_function=discover_fsc_sc2_info,
    check_function=check_fsc_sc2_info,
)
