#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    all_of,
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    get_value_store,
    OIDEnd,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)
from cmk.plugins.lib.humidity import check_humidity
from cmk.plugins.lib.temperature import check_temperature, TempParamType

# .1.3.6.1.4.1.18248.20.1.2.1.1.1.1 0
# .1.3.6.1.4.1.18248.20.1.2.1.1.1.2 0
# .1.3.6.1.4.1.18248.20.1.2.1.1.1.3 0
# .1.3.6.1.4.1.18248.20.1.2.1.1.2.1 249
# .1.3.6.1.4.1.18248.20.1.2.1.1.2.2 317
# .1.3.6.1.4.1.18248.20.1.2.1.1.2.3 69
# .1.3.6.1.4.1.18248.20.1.2.1.1.3.1 0
# .1.3.6.1.4.1.18248.20.1.2.1.1.3.2 3
# .1.3.6.1.4.1.18248.20.1.2.1.1.3.3 0

_MAP_SENSOR_TYPE = {
    "1": "temp",
    "2": "humidity",
    "3": "dewpoint",
}

_MAP_UNITS = {
    "0": "c",
    "1": "f",
    "2": "k",
    "3": "percent",
}

_MAP_STATES: Mapping[str, tuple[int, str]] = {
    "0": (0, "OK"),
    "1": (3, "not available"),
    "2": (1, "over-flow"),
    "3": (1, "under-flow"),
    "4": (2, "error"),
}

type _SensorData = tuple[tuple[int, str], float, str]
type Section = Mapping[str, Mapping[str, _SensorData]]


def parse_papouch_th2e_sensors(string_table: StringTable) -> Section | None:
    parsed: dict[str, dict[str, _SensorData]] = {}
    for oidend, state, reading_str, unit in string_table:
        if state != "3":
            sensor_ty = _MAP_SENSOR_TYPE[oidend]
            sensor_unit = _MAP_UNITS[unit]
            parsed.setdefault(sensor_ty, {})
            parsed[sensor_ty].setdefault(
                f"Sensor {oidend}",
                (
                    _MAP_STATES[state],
                    float(reading_str) / 10,
                    sensor_unit,
                ),
            )

    return parsed or None


def _discover_temp(section: Section, what: str) -> DiscoveryResult:
    for item in section[what]:
        yield Service(item=item)


def _check_temp(item: str, params: TempParamType, section: Section, what: str) -> CheckResult:
    if item in section[what]:
        (state, state_readable), reading, unit = section[what][item]
        yield from check_temperature(
            reading,
            params,
            unique_name=f"papouch_th2e_sensors_{what}_{item}",
            value_store=get_value_store(),
            dev_unit=unit,
            dev_status=state,
            dev_status_name=state_readable,
        )


def discover_papouch_th2e_sensors(section: Section) -> DiscoveryResult:
    yield from _discover_temp(section, "temp")


def check_papouch_th2e_sensors(item: str, params: TempParamType, section: Section) -> CheckResult:
    yield from _check_temp(item, params, section, "temp")


snmp_section_papouch_th2e_sensors = SimpleSNMPSection(
    name="papouch_th2e_sensors",
    detect=all_of(
        contains(".1.3.6.1.2.1.1.1.0", "th2e"),
        startswith(".1.3.6.1.2.1.1.2.0", ".0.10.43.6.1.4.1"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.18248.20.1.2.1.1",
        oids=[OIDEnd(), "1", "2", "3"],
    ),
    parse_function=parse_papouch_th2e_sensors,
)


check_plugin_papouch_th2e_sensors = CheckPlugin(
    name="papouch_th2e_sensors",
    service_name="Temperature %s",
    discovery_function=discover_papouch_th2e_sensors,
    check_function=check_papouch_th2e_sensors,
    check_ruleset_name="temperature",
    check_default_parameters={},
)


def discover_papouch_th2e_sensors_dewpoint(section: Section) -> DiscoveryResult:
    yield from _discover_temp(section, "dewpoint")


def check_papouch_th2e_sensors_dewpoint(
    item: str, params: TempParamType, section: Section
) -> CheckResult:
    yield from _check_temp(item, params, section, "dewpoint")


check_plugin_papouch_th2e_sensors_dewpoint = CheckPlugin(
    name="papouch_th2e_sensors_dewpoint",
    service_name="Dew point %s",
    sections=["papouch_th2e_sensors"],
    discovery_function=discover_papouch_th2e_sensors_dewpoint,
    check_function=check_papouch_th2e_sensors_dewpoint,
    check_ruleset_name="temperature",
    check_default_parameters={},
)


def discover_papouch_th2e_sensors_humidity(section: Section) -> DiscoveryResult:
    for item in section["humidity"]:
        yield Service(item=item)


def check_papouch_th2e_sensors_humidity(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if item in section["humidity"]:
        (state, state_readable), reading, _unit = section["humidity"][item]
        yield Result(state=State(state), summary=f"Status: {state_readable}")
        yield from check_humidity(reading, params)


check_plugin_papouch_th2e_sensors_humidity = CheckPlugin(
    name="papouch_th2e_sensors_humidity",
    service_name="Humidity %s",
    sections=["papouch_th2e_sensors"],
    discovery_function=discover_papouch_th2e_sensors_humidity,
    check_function=check_papouch_th2e_sensors_humidity,
    check_ruleset_name="humidity",
    check_default_parameters={
        "levels": (30.0, 35.0),
        "levels_lower": (12.0, 8.0),
    },
)
