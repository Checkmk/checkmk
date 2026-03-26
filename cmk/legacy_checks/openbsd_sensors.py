#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    exists,
    get_value_store,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.elphase import check_elphase, ElPhase, ReadingWithState
from cmk.plugins.lib.fan import check_fan
from cmk.plugins.lib.temperature import check_temperature, TempParamType

_OPENBSD_MAP_STATE: Mapping[str, State] = {
    "0": State.UNKNOWN,
    "1": State.OK,
    "2": State.WARN,
    "3": State.CRIT,
}

_OPENBSD_MAP_TYPE: Mapping[str, str] = {
    "0": "temp",
    "1": "fan",
    "2": "voltage",
    "9": "indicator",
    "13": "drive",
    "21": "powersupply",
}

SensorEntry = Mapping[str, Any]
Section = Mapping[str, SensorEntry]


def parse_openbsd_sensors(string_table: StringTable) -> Section:
    parsed: dict[str, dict[str, Any]] = {}
    used_descriptions: set[str] = set()

    def get_item_name(name: str) -> str:
        idx = 0
        new_name = name
        while True:
            if new_name in used_descriptions:
                new_name = f"{name}/{idx}"
                idx += 1
            else:
                used_descriptions.add(new_name)
                break
        return new_name

    for descr, sensortype, value, unit, state in string_table:
        if sensortype not in _OPENBSD_MAP_TYPE:
            continue
        if (sensortype == "0" and value == "-273.15") or (
            sensortype in ["1", "2"] and float(value) == 0
        ):
            continue

        try:
            value_converted: float | str = float(value)
        except ValueError:
            value_converted = value

        item_name = get_item_name(descr)
        parsed[item_name] = {
            "state": _OPENBSD_MAP_STATE[state],
            "value": value_converted,
            "unit": unit,
            "type": _OPENBSD_MAP_TYPE[sensortype],
        }
    return parsed


def _discover_openbsd_sensors(section: Section, sensortype: str) -> DiscoveryResult:
    for key, values in section.items():
        if values["type"] == sensortype:
            yield Service(item=key)


def discover_openbsd_sensors(section: Section) -> DiscoveryResult:
    yield from _discover_openbsd_sensors(section, "temp")


def check_openbsd_sensors(item: str, params: TempParamType, section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return
    yield from check_temperature(
        data["value"],
        params,
        unique_name=f"openbsd_sensors_{item}",
        value_store=get_value_store(),
    )


snmp_section_openbsd_sensors = SimpleSNMPSection(
    name="openbsd_sensors",
    detect=exists(".1.3.6.1.4.1.30155.2.1.1.0"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.30155.2.1.2.1",
        oids=["2", "3", "5", "6", "7"],
    ),
    parse_function=parse_openbsd_sensors,
)


check_plugin_openbsd_sensors = CheckPlugin(
    name="openbsd_sensors",
    service_name="Temperature %s",
    discovery_function=discover_openbsd_sensors,
    check_function=check_openbsd_sensors,
    check_ruleset_name="temperature",
    check_default_parameters={},
)


def discover_openbsd_sensors_fan(section: Section) -> DiscoveryResult:
    yield from _discover_openbsd_sensors(section, "fan")


def check_openbsd_sensors_fan(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if not (data := section.get(item)):
        return
    yield from check_fan(data["value"], params)


check_plugin_openbsd_sensors_fan = CheckPlugin(
    name="openbsd_sensors_fan",
    service_name="Fan %s",
    sections=["openbsd_sensors"],
    discovery_function=discover_openbsd_sensors_fan,
    check_function=check_openbsd_sensors_fan,
    check_ruleset_name="hw_fans",
    check_default_parameters={
        "lower": (500, 300),
        "upper": (8000, 8400),
    },
)


def discover_openbsd_sensors_voltage(section: Section) -> DiscoveryResult:
    yield from _discover_openbsd_sensors(section, "voltage")


def check_openbsd_sensors_voltage(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if not (data := section.get(item)):
        return
    elphase = ElPhase(voltage=ReadingWithState(value=data["value"]))
    yield from check_elphase(params, elphase)


check_plugin_openbsd_sensors_voltage = CheckPlugin(
    name="openbsd_sensors_voltage",
    service_name="Voltage Type %s",
    sections=["openbsd_sensors"],
    discovery_function=discover_openbsd_sensors_voltage,
    check_function=check_openbsd_sensors_voltage,
    check_ruleset_name="el_inphase",
    check_default_parameters={},
)


def discover_openbsd_sensors_powersupply(section: Section) -> DiscoveryResult:
    yield from _discover_openbsd_sensors(section, "powersupply")


def check_openbsd_sensors_powersupply(item: str, section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return
    yield Result(state=data["state"], summary=f"Status: {data['value']}")


check_plugin_openbsd_sensors_powersupply = CheckPlugin(
    name="openbsd_sensors_powersupply",
    service_name="Powersupply %s",
    sections=["openbsd_sensors"],
    discovery_function=discover_openbsd_sensors_powersupply,
    check_function=check_openbsd_sensors_powersupply,
)


def discover_openbsd_sensors_indicator(section: Section) -> DiscoveryResult:
    yield from _discover_openbsd_sensors(section, "indicator")


def check_openbsd_sensors_indicator(item: str, section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return
    yield Result(state=data["state"], summary=f"Status: {data['value']}")


check_plugin_openbsd_sensors_indicator = CheckPlugin(
    name="openbsd_sensors_indicator",
    service_name="Indicator %s",
    sections=["openbsd_sensors"],
    discovery_function=discover_openbsd_sensors_indicator,
    check_function=check_openbsd_sensors_indicator,
)


def discover_openbsd_sensors_drive(section: Section) -> DiscoveryResult:
    yield from _discover_openbsd_sensors(section, "drive")


def check_openbsd_sensors_drive(item: str, section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return
    yield Result(state=data["state"], summary=f"Status: {data['value']}")


check_plugin_openbsd_sensors_drive = CheckPlugin(
    name="openbsd_sensors_drive",
    service_name="Drive %s",
    sections=["openbsd_sensors"],
    discovery_function=discover_openbsd_sensors_drive,
    check_function=check_openbsd_sensors_drive,
)
