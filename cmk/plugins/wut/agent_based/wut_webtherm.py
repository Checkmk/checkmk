#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)
from cmk.plugins.lib.humidity import check_humidity
from cmk.plugins.lib.temperature import check_temperature, TempParamType

_TYPE_TABLE_IDX = (1, 2, 3, 6, 7, 8, 9, 16, 18, 36, 37, 38, 42)

Section = dict[str, dict[str, Any]]


def parse_wut_webtherm(string_table: Sequence[StringTable]) -> Section:
    map_sensor_type = {
        "1": "temp",
        "2": "humid",
        "3": "air_pressure",
    }
    parsed: Section = {}
    for webtherm_type, info in zip(_TYPE_TABLE_IDX, string_table):
        for sensor_id, reading_de, reading_en in info:
            reading_str = reading_en or reading_de.replace(",", ".")
            if not reading_str or "---" in reading_str:
                continue

            # Dependent on webtherm_type we have to determine
            # which sensors are available. Feel free to
            # declare more sensor types here.
            # We have only temperature sensors
            if webtherm_type <= 9:  # TODO: this is just a guess
                parsed[sensor_id] = {
                    "type": "temp",
                    "reading": float(reading_str),
                }
            # Here we have three different types of sensors:
            # 1 = temp, 2 = humid, 3 = air pressure
            else:
                parsed[sensor_id] = {
                    "type": map_sensor_type[sensor_id],
                    "reading": float(reading_str),
                }

    return parsed


def discover_wut_webtherm(section: Section) -> DiscoveryResult:
    yield from (
        Service(item=sensor_id) for sensor_id, values in section.items() if values["type"] == "temp"
    )


def check_wut_webtherm(item: str, params: TempParamType, section: Section) -> CheckResult:
    if item in section:
        yield from check_temperature(
            reading=section[item]["reading"],
            params=params,
            unique_name=f"wut_webtherm_{item}",
            value_store=get_value_store(),
        )


def discover_wut_webtherm_pressure(section: Section) -> DiscoveryResult:
    yield from (
        Service(item=sensor_id)
        for sensor_id, values in section.items()
        if values["type"] == "air_pressure"
    )


def check_wut_webtherm_pressure(item: str, section: Section) -> CheckResult:
    if item in section:
        yield Result(state=State.OK, summary=f"{section[item]['reading']:.2f} hPa")


def discover_wut_webtherm_humidity(section: Section) -> DiscoveryResult:
    yield from (
        Service(item=sensor_id)
        for sensor_id, values in section.items()
        if values["type"] == "humid"
    )


def check_wut_webtherm_humidity(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if item in section:
        yield from check_humidity(section[item]["reading"], params)


snmp_section_wut_webtherm = SNMPSection(
    name="wut_webtherm",
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.5040.1.2."),
    fetch=[
        SNMPTree(
            base=f".1.3.6.1.4.1.5040.1.2.{idx}.1",
            oids=[
                "2.1.1",  # WebGraph-Thermo-Hygro-Barometer-MIB::wtWebGraphThermoBaroSensorNo
                "3.1.1",  # WebGraph-Thermo-Hygro-Barometer-MIB::wtWebGraphThermoBaroTempValue
                "8.1.1",  # WebGraph-Thermo-Hygro-Barometer-MIB::wtWebGraphThermoBaroTempValuePkt
            ],
        )
        for idx in _TYPE_TABLE_IDX
    ],
    parse_function=parse_wut_webtherm,
)


check_plugin_wut_webtherm = CheckPlugin(
    name="wut_webtherm",
    service_name="Temperature %s",
    discovery_function=discover_wut_webtherm,
    check_function=check_wut_webtherm,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (30.0, 35.0),
    },
)

check_plugin_wut_webtherm_pressure = CheckPlugin(
    name="wut_webtherm_pressure",
    service_name="Pressure %s",
    sections=["wut_webtherm"],
    discovery_function=discover_wut_webtherm_pressure,
    check_function=check_wut_webtherm_pressure,
)

check_plugin_wut_webtherm_humidity = CheckPlugin(
    name="wut_webtherm_humidity",
    service_name="Humidity %s",
    sections=["wut_webtherm"],
    discovery_function=discover_wut_webtherm_humidity,
    check_function=check_wut_webtherm_humidity,
    check_ruleset_name="humidity",
    check_default_parameters={
        "levels": (60.0, 65.0),
        "levels_lower": (40.0, 35.0),
    },
)
