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
from cmk.plugins.lib.temperature import (
    check_temperature,
    render_temp,
    temp_unitsym,
    TempParamDict,
    TempParamType,
)


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
    min: float
    max: float


class SensorWarnTemp:
    PHY = 80
    INLET = 30
    ASIC = 80
    CPU = 80
    DDR = 60
    DDR_INLET = 40
    MAINBOARD = 35
    INTERNAL = 45


class SensorCritTemp:
    PHY = 90
    INLET = 40
    ASIC = 90
    CPU = 90
    DDR = 70
    DDR_INLET = 45
    MAINBOARD = 40
    INTERNAL = 50


Section = Mapping[str, TemperatureSensor]

aruba_sw_temp_check_default_parameters = TempParamDict(
    input_unit="c",
)


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
    def get_aruba_default_temp(name: str) -> tuple[float, float]:
        if "CPU" in name:
            return (SensorWarnTemp.CPU, SensorCritTemp.CPU)
        if "ASIC" in name:
            return (SensorWarnTemp.ASIC, SensorCritTemp.ASIC)
        if "DDR" in name:
            if "Inlet" in name:
                return (SensorWarnTemp.DDR_INLET, SensorCritTemp.DDR_INLET)
            return (SensorWarnTemp.DDR, SensorCritTemp.DDR)
        if "Inlet" in name:
            return (SensorWarnTemp.INLET, SensorCritTemp.INLET)
        if "PHY" in name:
            return (SensorWarnTemp.PHY, SensorCritTemp.PHY)
        if "Internal" in name:
            return (SensorWarnTemp.INTERNAL, SensorCritTemp.INTERNAL)

        return (SensorWarnTemp.MAINBOARD, SensorCritTemp.MAINBOARD)

    temp = section.get(item)
    if not temp:
        return

    warn, crit = get_aruba_default_temp(temp.name)

    if SensorStatus[temp.status] != SensorStatus.fault:
        yield from check_temperature(
            reading=temp.cur,
            params=params,
            unique_name=item,
            value_store=get_value_store(),
            dev_levels=(warn, crit),
        )

    yield Result(
        state=SensorStateMapping[SensorStatus[temp.status]],
        summary=f"Device status: {temp.status}",
    )

    yield Result(
        state=State.OK,
        summary=f"Min temperature: {
            render_temp(temp.min, aruba_sw_temp_check_default_parameters['input_unit'])
        } {temp_unitsym[aruba_sw_temp_check_default_parameters['input_unit']]}",
    )

    yield Result(
        state=State.OK,
        summary=f"Max temperature: {
            render_temp(temp.max, aruba_sw_temp_check_default_parameters['input_unit'])
        } {temp_unitsym[aruba_sw_temp_check_default_parameters['input_unit']]}",
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


check_plugin_aruba_sw_temp = CheckPlugin(
    name="aruba_sw_temp",
    sections=["aruba_sw_temp"],
    service_name="Temperature %s",
    discovery_function=discover_aruba_sw_temp,
    check_function=check_aruba_sw_temp,
    check_ruleset_name="temperature",
    check_default_parameters=aruba_sw_temp_check_default_parameters,
)
