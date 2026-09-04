#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# vutlan is not a typo!
# MIB can also be browsed on
# https://mibs.observium.org/mib/SKYCONTROL-SYSTEM-MIB/#
# NOTE: the unit is not given in the SNMP walk, it is %

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    OIDEnd,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.humidity import check_humidity
from cmk.plugins.vutlan.lib import DETECT_VUTLAN_EMS

Section = Mapping[str, float]


def parse_vutlan_ems_humidity(string_table: StringTable) -> Section:
    parsed = {}
    for line in string_table:
        if line[0].startswith("202"):
            # all OIDs 202xxx are humidity-related
            parsed[line[1]] = float(line[2])
    return parsed


snmp_section_vutlan_ems_humidity = SimpleSNMPSection(
    name="vutlan_ems_humidity",
    parse_function=parse_vutlan_ems_humidity,
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


def discover_vutlan_ems_humidity(section: Section) -> DiscoveryResult:
    yield from (Service(item=sensor_name) for sensor_name in section)


def check_vutlan_ems_humidity(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if (reading := section.get(item)) is None:
        return
    yield from check_humidity(reading, params)


check_plugin_vutlan_ems_humidity = CheckPlugin(
    name="vutlan_ems_humidity",
    service_name="Humidity %s",
    discovery_function=discover_vutlan_ems_humidity,
    check_function=check_vutlan_ems_humidity,
    check_ruleset_name="humidity",
    check_default_parameters={
        "levels": (60.0, 70.0),
        "levels_lower": (30.0, 15.0),
    },
)
