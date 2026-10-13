#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# vutlan is not a typo!
# MIB can also be browsed on
# https://mibs.observium.org/mib/SKYCONTROL-SYSTEM-MIB/#

from collections.abc import Mapping

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    OIDEnd,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.vutlan.lib import DETECT_VUTLAN_EMS

Section = Mapping[str, bool]


def parse_vutlan_ems_leakage(string_table: StringTable) -> Section:
    parsed = {}
    for line in string_table:
        if line[0].startswith("107"):
            # all OIDs 107xxx are leakage-related
            parsed[line[1]] = bool(int(line[2]))
    return parsed


snmp_section_vutlan_ems_leakage = SimpleSNMPSection(
    name="vutlan_ems_leakage",
    parse_function=parse_vutlan_ems_leakage,
    detect=DETECT_VUTLAN_EMS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.39052.1.3.1",
        oids=[
            OIDEnd(),
            "7",  # vutlan.mib::ctlUnitElementName (can be user-defined)
            "9",  # vutlan.mib::ctlUnitElementValue
        ],
    ),
)


def discover_vutlan_ems_leakage(section: Section) -> DiscoveryResult:
    yield from (Service(item=sensor_name) for sensor_name in section)


def check_vutlan_ems_leakage(item: str, section: Section) -> CheckResult:
    leakage_detected = section.get(item)
    if leakage_detected is None:
        return

    if leakage_detected:
        yield Result(state=State.CRIT, summary="Leak detected")
        return

    yield Result(state=State.OK, summary="No leak detected")


check_plugin_vutlan_ems_leakage = CheckPlugin(
    name="vutlan_ems_leakage",
    service_name="Leakage %s",
    discovery_function=discover_vutlan_ems_leakage,
    check_function=check_vutlan_ems_leakage,
)
