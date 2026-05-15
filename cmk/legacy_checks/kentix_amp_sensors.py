#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any, TypedDict

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    render,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.kentix.lib import DETECT_KENTIX
from cmk.plugins.lib.humidity import check_humidity
from cmk.plugins.lib.temperature import check_temperature, TempParamType

# .1.3.6.1.4.1.37954.1.2.7.1.0 RZ1SE-KLIMA-NEU  sensor name
# .1.3.6.1.4.1.37954.1.2.7.2.0 159              temperature     INTEGER (0..1000)
# .1.3.6.1.4.1.37954.1.2.7.3.0 474              humidity        INTEGER (0..1000)
# .1.3.6.1.4.1.37954.1.2.7.4.0 48               dew point       INTEGER (0..1000)
# .1.3.6.1.4.1.37954.1.2.7.5.0 0                carbon monoxide INTEGER (-100..100) # in percent
# .1.3.6.1.4.1.37954.1.2.7.6.0 0                motion          INTEGER (0..100)
# .1.3.6.1.4.1.37954.1.2.7.7.0 0                digital in 1    INTEGER (0..1)      # leakage sensor: 0 (no alarm, connected)
#                                                                                                     1 (alarm or disconnected)
# .1.3.6.1.4.1.37954.1.2.7.8.0 0                digital in 2    INTEGER (0..1)
# .1.3.6.1.4.1.37954.1.2.7.9.0 0                digital out     INTEGER (0..1)
# .1.3.6.1.4.1.37954.1.2.7.10.0 0               comError        INTEGER (0..1)


class Sensor(TypedDict, total=False):
    temp: float
    humidity: float
    smoke: int
    leakage: int


Section = Mapping[str, Sensor]


def parse_kentix_amp_sensors(string_table: Sequence[StringTable]) -> Section:
    info_flattened = []
    for i in range(0, len(string_table[0]), 10):
        info_flattened.append([a[0] for a in string_table[0][i : i + 10]])

    parsed: dict[str, Sensor] = {}
    for line in info_flattened:
        if line[0] != "":
            sensor: Sensor = {
                "temp": float(line[1]) / 10,
                "humidity": float(line[2]) / 10,
                "smoke": int(line[4]),
            }
            if line[6] != "":
                sensor["leakage"] = int(line[6])
            parsed[line[0]] = sensor

    return parsed


snmp_section_kentix_amp_sensors = SNMPSection(
    name="kentix_amp_sensors",
    detect=DETECT_KENTIX,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.37954.1",
            oids=["2"],
        )
    ],
    parse_function=parse_kentix_amp_sensors,
)


def discover_kentix_amp_sensors(section: Section) -> DiscoveryResult:
    yield from (Service(item=key) for key in section)


def check_kentix_amp_sensors(item: str, params: TempParamType, section: Section) -> CheckResult:
    if (sensor := section.get(item)) is None:
        return
    yield from check_temperature(
        reading=sensor["temp"],
        params=params,
        unique_name=f"kentix_amp_sensors_{item}",
        value_store=get_value_store(),
    )


check_plugin_kentix_amp_sensors = CheckPlugin(
    name="kentix_amp_sensors",
    service_name="Temperature %s",
    discovery_function=discover_kentix_amp_sensors,
    check_function=check_kentix_amp_sensors,
    check_ruleset_name="temperature",
    check_default_parameters={},
)


def check_kentix_amp_sensors_humidity(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if (sensor := section.get(item)) is None:
        return
    yield from check_humidity(sensor["humidity"], params)


check_plugin_kentix_amp_sensors_humidity = CheckPlugin(
    name="kentix_amp_sensors_humidity",
    service_name="Humidity %s",
    sections=["kentix_amp_sensors"],
    discovery_function=discover_kentix_amp_sensors,
    check_function=check_kentix_amp_sensors_humidity,
    check_ruleset_name="humidity",
    check_default_parameters={},
)


def check_kentix_amp_sensors_smoke(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if (sensor := section.get(item)) is None:
        return
    yield from check_levels_v1(
        sensor["smoke"],
        metric_name="smoke_perc",
        levels_upper=params["levels"],
        render_func=render.percent,
        boundaries=(0, 100),
    )


check_plugin_kentix_amp_sensors_smoke = CheckPlugin(
    name="kentix_amp_sensors_smoke",
    service_name="Smoke Detector %s",
    sections=["kentix_amp_sensors"],
    discovery_function=discover_kentix_amp_sensors,
    check_function=check_kentix_amp_sensors_smoke,
    check_ruleset_name="smoke",
    check_default_parameters={"levels": (1.0, 5.0)},
)


def check_kentix_amp_sensors_leakage(item: str, section: Section) -> CheckResult:
    if (sensor := section.get(item)) is None:
        return
    if sensor.get("leakage", 0) > 0:
        yield Result(state=State.CRIT, summary="Alarm or disconnected")
    else:
        yield Result(state=State.OK, summary="Connected")


check_plugin_kentix_amp_sensors_leakage = CheckPlugin(
    name="kentix_amp_sensors_leakage",
    service_name="Leakage %s",
    sections=["kentix_amp_sensors"],
    discovery_function=discover_kentix_amp_sensors,
    check_function=check_kentix_amp_sensors_leakage,
)
