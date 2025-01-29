#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import NamedTuple

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
from cmk.plugins.lib.ciena_ces import (
    DETECT_CIENA_5142,
    DETECT_CIENA_5171,
    LeoTempSensorState,
    TceHealthStatus,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamType


class TemperatureReading(NamedTuple):
    temperature: int
    device_status: int
    device_status_name: str


Section = Mapping[str, TemperatureReading]


def _parse_temp_and_device_state_5171(device_status_str: str, temp_str: str) -> TemperatureReading:
    device_status = TceHealthStatus(device_status_str)
    return TemperatureReading(
        temperature=int(temp_str),
        device_status=0 if device_status == TceHealthStatus.normal else 2,
        device_status_name=device_status.name,
    )


def _item_description_5171(oid_end: str) -> str:
    """

    >>> _item_description_5171('14.1')
    'sensor 14 slot 1'
    """
    sensor, slot = oid_end.split(".")
    return f"sensor {sensor} slot {slot}"


def parse_ciena_temperature_5171(string_table: StringTable) -> Section:
    """
    >>> from pprint import pprint
    >>> string_table = [['14.1', '2', '33'], ['2.1', '3', '100']]
    >>> pprint(parse_ciena_temperature_5171(string_table))
    {'sensor 14 slot 1': TemperatureReading(temperature=33, device_status=0, device_status_name='normal'),
     'sensor 2 slot 1': TemperatureReading(temperature=100, device_status=2, device_status_name='warning')}
    """
    return {
        _item_description_5171(oid_end): _parse_temp_and_device_state_5171(*row)
        for oid_end, *row in string_table
    }


def _parse_temp_and_device_state_5142(device_status_str: str, temp_str: str) -> TemperatureReading:
    device_status = LeoTempSensorState(device_status_str)
    return TemperatureReading(
        temperature=int(temp_str),
        device_status=0 if device_status == LeoTempSensorState.normal else 2,
        device_status_name=device_status.name,
    )


def parse_ciena_temperature_5142(string_table: StringTable) -> Section:
    """
    >>> parse_ciena_temperature_5142([['1', '1', '24']])
    {'1': TemperatureReading(temperature=24, device_status=0, device_status_name='normal')}
    """
    return {sensor: _parse_temp_and_device_state_5142(*row) for sensor, *row in string_table}


def discover_ciena_temperature(section: Section) -> DiscoveryResult:
    yield from (Service(item=i) for i in section)


def check_ciena_temperature(item: str, params: TempParamType, section: Section) -> CheckResult:
    if item not in section:
        return
    yield from check_temperature(
        section[item].temperature,
        params,
        unique_name="",
        value_store=get_value_store(),
        dev_status=section[item].device_status,
        dev_status_name=section[item].device_status_name,
    )


snmp_section_ciena_temperature_5171 = SimpleSNMPSection(
    name="ciena_temperature_5171",
    parse_function=parse_ciena_temperature_5171,
    parsed_section_name="ciena_temperature",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1271.2.1.5.1.2.1.4.13.1",
        oids=[
            OIDEnd(),  # Index is cienaCesChassisModuleTempHealthSubCategory,cienaCesChassisModuleTempHealthOriginIndex
            "3",  # cienaCesChassisModuleTempHealthState
            "4",  # cienaCesChassisModuleTempHealthCurrMeasurement
        ],
    ),
    detect=DETECT_CIENA_5171,
)

snmp_section_ciena_temperature_5142 = SimpleSNMPSection(
    name="ciena_temperature_5142",
    parse_function=parse_ciena_temperature_5142,
    parsed_section_name="ciena_temperature",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.6141.2.60.11.1.1.5.1.1",
        oids=[
            "1",  # wwpLeosChassisTempSensorNum
            "5",  # wwpLeosChassisTempSensorState
            "2",  # wwpLeosChassisTempSensorValue
        ],
    ),
    detect=DETECT_CIENA_5142,
)
check_plugin_ciena_temperature = CheckPlugin(
    name="ciena_temperature",
    sections=["ciena_temperature"],
    service_name="Temperature %s",
    discovery_function=discover_ciena_temperature,
    check_function=check_ciena_temperature,
    check_ruleset_name="temperature",
    check_default_parameters={},
)
