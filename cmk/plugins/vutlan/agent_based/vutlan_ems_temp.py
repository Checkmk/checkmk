#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# vutlan is not a typo!
# MIB can also be browsed on
# https://mibs.observium.org/mib/SKYCONTROL-SYSTEM-MIB/#
# NOTE: the unit is not given in the SNMP walk, it is °C

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping, MutableMapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    OIDEnd,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamType
from cmk.plugins.vutlan.lib import DETECT_VUTLAN_EMS

Section = Mapping[str, float]


def parse_vutlan_ems_temp(string_table: StringTable) -> Section:
    parsed = {}
    for line in string_table:
        if line[0].startswith("201"):
            # all OIDs 201xxx are temperature-related
            parsed[line[1]] = float(line[2])
    return parsed


snmp_section_vutlan_ems_temp = SimpleSNMPSection(
    name="vutlan_ems_temp",
    parse_function=parse_vutlan_ems_temp,
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


def discover_vutlan_ems_temp(section: Section) -> DiscoveryResult:
    yield from (Service(item=sensor_name) for sensor_name in section)


def check_vutlan_ems_temp(item: str, params: TempParamType, section: Section) -> CheckResult:
    yield from check_vutlan_ems_temp_impl(item, params, section, get_value_store())


def check_vutlan_ems_temp_impl(
    item: str,
    params: TempParamType,
    section: Section,
    value_store: MutableMapping[str, Any],
) -> CheckResult:
    if (reading := section.get(item)) is None:
        return
    yield from check_temperature(
        reading,
        params,
        unique_name="vutlan_ems",  # unique name is needed to activate trend computing
        value_store=value_store,
    )


check_plugin_vutlan_ems_temp = CheckPlugin(
    name="vutlan_ems_temp",
    service_name="Temperature %s",
    discovery_function=discover_vutlan_ems_temp,
    check_function=check_vutlan_ems_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (35.0, 40.0),
        "levels_lower": (0.0, -1.0),
    },
)
