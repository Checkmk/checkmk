#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.netextreme import DETECT_NETEXTREME
from cmk.plugins.lib.temperature import check_temperature, TempParamType


@dataclass
class VSPSwitchTempInfo:
    name: str
    temperature: float


VSPSwitchesSection = Mapping[str, VSPSwitchTempInfo]


def parse_vsp_switches_temperature(string_table: StringTable) -> VSPSwitchesSection:
    section: dict[str, VSPSwitchTempInfo] = {}
    for line in string_table:
        item = line[0] or line[2]
        if item:
            section[item] = VSPSwitchTempInfo(
                name=item,
                temperature=float(line[1]),
            )
    return section


snmp_section_extreme_vsp_switches_temperature = SimpleSNMPSection(
    name="extreme_vsp_switches_temperature",
    parse_function=parse_vsp_switches_temperature,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2272.1.101.1.1",
        oids=[
            # RAPID-CITY.mib
            "2.1.2",  # rcVossSystemTemperatureSensorDescription
            "2.1.3",  # rcVossSystemTemperatureTemperature -> expressed in Celsius
            # Unknown mib
            "6.1.4.1",  # Another source for the description which 2.1.2 sometimes misses
        ],
    ),
    detect=DETECT_NETEXTREME,
)


def discover_vsp_switches_temperature(section: VSPSwitchesSection) -> DiscoveryResult:
    for vsp_switch in section:
        yield Service(item=vsp_switch)


def check_vsp_switches_temperature(
    item: str,
    params: TempParamType,
    section: VSPSwitchesSection,
) -> CheckResult:
    if (vsp_switch := section.get(item)) is None:
        return

    yield from check_temperature(
        reading=vsp_switch.temperature,
        params=params,
        unique_name=f"vsp_switch_{item}",
        value_store=get_value_store(),
    )


check_plugin_extreme_vsp_switches_temperature = CheckPlugin(
    name="extreme_vsp_switches_temperature",
    service_name="VSP Switch %s Temperature",
    discovery_function=discover_vsp_switches_temperature,
    check_function=check_vsp_switches_temperature,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (50.0, 60.0),
    },
)
