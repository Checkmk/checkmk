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
    return {
        line[0]: VSPSwitchTempInfo(
            name=line[0],
            temperature=float(line[1]),
        )
        for line in string_table
    }


snmp_section_extreme_vsp_switches_temperature = SimpleSNMPSection(
    name="extreme_vsp_switches_temperature",
    parse_function=parse_vsp_switches_temperature,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2272.1.101.1.1.2.1",
        oids=[
            "2",  # rcVossSystemTemperatureSensorDescription
            "3",  # rcVossSystemTemperatureTemperature -> expressed in Celsius
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
