#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from enum import IntEnum
from typing import NamedTuple

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    exists,
    get_value_store,
    OIDEnd,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamDict, TempParamType


class SensorStatus(IntEnum):
    fault = 0
    normal = 1
    emergency = 2


SensorStateMapping = {
    SensorStatus.fault: State.WARN,
    SensorStatus.normal: State.OK,
    SensorStatus.emergency: State.CRIT,
}


class TemperatureSensor(NamedTuple):
    name: str
    status: str
    cur: float
    max: float
    min: float


Section = Mapping[str, TemperatureSensor]


def parse_aruba_sw_temp(string_table: StringTable) -> Section:
    return {
        entry[1]: TemperatureSensor(
            name=entry[1],
            status=entry[2],
            cur=int(entry[3]) / 1000,
            min=int(entry[4]) / 1000,
            max=int(entry[5]) / 1000,
        )
        for entry in string_table
    }


def discover_aruba_sw_temp(section: Section) -> DiscoveryResult:
    for item, entry in section.items():
        yield Service(item=item)


def check_aruba_sw_temp(
    item: str,
    params: TempParamType,
    section: Section,
) -> CheckResult:
    temp = section.get(item)
    if not temp:
        return

    if SensorStatus[temp.status] != SensorStatus.fault:
        yield from check_temperature(
            reading=temp.cur,
            params=params,
            unique_name=item,
            value_store=get_value_store(),
            dev_levels=(temp.max * 0.95, temp.max),
            dev_levels_lower=(temp.min * 1.05, temp.min),
        )

    yield Result(
        state=SensorStateMapping[SensorStatus[temp.status]],
        summary=f"Device status: {temp.status}",
    )


snmp_section_aruba_sw_temp_status = SimpleSNMPSection(
    name="aruba_sw_temp",
    detect=exists(".1.3.6.1.4.1.47196.4.1.1.3.11.3.1.1.*"),
    parse_function=parse_aruba_sw_temp,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.47196.4.1.1.3.11.3.1.1",
        oids=[
            OIDEnd(),
            "5",  # sensorName
            "6",  # sensorState
            "7",  # sensorTemp
            "8",  # sensorMinTemp
            "9",  # sensorMaxTemp
        ],
    ),
)

aruba_sw_temp_check_default_parameters = TempParamDict(
    input_unit="c",
    device_levels_handling="usrdefault",
)


check_plugin_aruba_sw_temp = CheckPlugin(
    name="aruba_sw_temp",
    sections=["aruba_sw_temp"],
    service_name="Temperature %s",
    discovery_function=discover_aruba_sw_temp,
    check_function=check_aruba_sw_temp,
    check_ruleset_name="temperature",
    check_default_parameters=aruba_sw_temp_check_default_parameters,
)
