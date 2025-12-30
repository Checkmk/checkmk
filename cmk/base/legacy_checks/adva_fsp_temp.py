#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    equals,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamType


@dataclass(frozen=True)
class Sensor:
    temperature: float
    threshold_low: float
    threshold_high: float


type Section = Mapping[str, Sensor]


def _is_connected(raw_temp: str, description: str) -> bool:
    return bool(description) and bool(raw_temp)


def parse_adva_fsp_temp(string_table: StringTable) -> Section:
    return {
        name: Sensor(
            temperature=float(raw_temp) / 10,
            threshold_high=float(raw_high) / 10,
            threshold_low=float(raw_low) / 10,
        )
        for raw_temp, raw_high, raw_low, description, name in string_table
        if _is_connected(raw_temp, description)
    }


def discover_adva_fsp_temp(section: Section) -> DiscoveryResult:
    yield from (
        Service(item=name) for name, sensor in section.items() if sensor.temperature > -273.0
    )


def check_adva_fsp_temp(item: str, params: TempParamType, section: Section) -> CheckResult:
    if (sensor := section.get(item)) is None:
        return

    if sensor.temperature <= -273.0:
        yield Result(state=State.UNKNOWN, summary="Invalid sensor data")

    yield from check_temperature(
        sensor.temperature,
        params,
        dev_levels=(sensor.threshold_high, sensor.threshold_high),
        dev_levels_lower=(
            (sensor.threshold_low, sensor.threshold_low) if sensor.threshold_low > -273 else None
        ),
    )


snmp_section_adva_fsp_temp = SimpleSNMPSection(
    name="adva_fsp_temp",
    detect=equals(".1.3.6.1.2.1.1.1.0", "Fiber Service Platform F7"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2544",
        oids=[
            "1.11.2.4.2.1.1.1",
            "1.11.2.4.2.1.1.2",
            "1.11.2.4.2.1.1.3",
            "2.5.5.1.1.1",
            "2.5.5.2.1.5",
        ],
    ),
    parse_function=parse_adva_fsp_temp,
)


check_plugin_adva_fsp_temp = CheckPlugin(
    name="adva_fsp_temp",
    service_name="Temperature %s",
    discovery_function=discover_adva_fsp_temp,
    check_function=check_adva_fsp_temp,
    check_ruleset_name="temperature",
    check_default_parameters={},
)
