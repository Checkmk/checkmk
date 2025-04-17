#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from dataclasses import dataclass

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
from cmk.plugins.lib.datapower import DETECT
from cmk.plugins.lib.temperature import check_temperature, TempParamDict

DATAPOWER_TEMP_STATUS_MAPPING = {
    "8": Result(state=State.CRIT, summary="device status: failure"),
    "9": Result(state=State.UNKNOWN, summary="device status: noReading"),
    "10": Result(state=State.CRIT, summary="device status: invalid"),
}


@dataclass(frozen=True, kw_only=True)
class Temp:
    name: str
    temp: float
    status: Result | None
    dev_levels: tuple[float, float] | None


Section = Mapping[str, Temp]


def parse_datapower_temp(string_table: StringTable) -> Section:
    return {
        name.strip("Temperature "): Temp(
            name=name.strip("Temperature "),
            temp=float(temp),
            status=DATAPOWER_TEMP_STATUS_MAPPING.get(status),
            dev_levels=_create_dev_levels(warn, crit),
        )
        for name, temp, warn, status, crit in string_table
    }


def _create_dev_levels(warn: str, crit: str) -> tuple[float, float] | None:
    try:
        return (float(warn), float(crit))
    except ValueError:
        return None


snmp_section_datapower_temp = SimpleSNMPSection(
    name="datapower_temp",
    parse_function=parse_datapower_temp,
    detect=DETECT,
    fetch=SNMPTree(
        ".1.3.6.1.4.1.14685.3.1.141.1",
        [
            "1",  # dpStatusEnvironmentalSensorsName
            "2",  # dpStatusEnvironmentalSensorsValue
            "3",  # dpStatusEnvironmentalSensorsUpperNonCriticalThreshold
            "5",  # dpStatusEnvironmentalSensorsReadingStatus
            "6",  # dpStatusEnvironmentalSensorsUpperCriticalThreshold
        ],
    ),
)


def discover_datapower_temp(section: Section) -> DiscoveryResult:
    yield from (Service(item=name) for name in section)


def check_datapower_temp(item: str, params: TempParamDict, section: Section) -> CheckResult:
    if (temp_value := section.get(item)) is None:
        return
    if temp_value.status:
        yield temp_value.status
        return
    yield from check_temperature(
        reading=temp_value.temp,
        params=params.get("levels"),
        dev_levels=temp_value.dev_levels,
    )


check_plugin_datapower_temp = CheckPlugin(
    name="datapower_temp",
    service_name="Temperature %s",
    discovery_function=discover_datapower_temp,
    check_function=check_datapower_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (65.0, 70.0),  # 70C recommended alarm level by IBM
    },
)
