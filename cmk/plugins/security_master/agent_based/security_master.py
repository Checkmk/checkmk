#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import contextlib
from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    OIDEnd,
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

#
# SNMP Infos
# .1.3.6.1.2.1.1 System description
# .1.3.6.1.4.1.35491.30.2.0 No of Sensors - max. 100
# .1.3.6.1.4.1.35491.30.3 Sensor Group1
#
# 11 values per sensor
# .1.3.6.1.4.1.35491.30.3.1.1.0 Sensor 1 ID
# .1.3.6.1.4.1.35491.30.3.1.2.0 Sensor 1 value
# .1.3.6.1.4.1.35491.30.3.1.3.0 Sensor 1 unit
# .1.3.6.1.4.1.35491.30.3.1.4.0 Sensor 1 valueint -> value *1000, without comma
# .1.3.6.1.4.1.35491.30.3.1.5.0 Sensor 1 name
# .1.3.6.1.4.1.35491.30.3.1.6.0 Sensor 1 alarmint
#                                        -1 = no value (also digi-input and output)
#                                         1 = lower critical alarm or green area (on digi-input)
#                                         2 = lower warning
#                                         3 = normal
#                                         4 = upper warning
#                                         5 = upper critical or red area (on digi-input)
# .1.3.6.1.4.1.35491.30.3.1.7.0 Sensor 1 LoLimitAlarmInt
# .1.3.6.1.4.1.35491.30.3.1.8.0 Sensor 1 LoLimitWarnInt
# .1.3.6.1.4.1.35491.30.3.1.9.0 Sensor 1 HiLimitWarnInt
# .1.3.6.1.4.1.35491.30.3.1.10.0 Sensor 1 HiLimitAlarmInt
# .1.3.6.1.4.1.35491.30.3.1.11.0 Sensor 1 HysterInt
#
# .1.3.6.1.4.1.35491.30.3.2.1.0 Sensor 2 ID
# .
# .
# .
# Here a List of known sensors
# sensors_ids = {
#    20: ("digital", "Schloss"),
#    22: ("digital", "Relaisadapter AC"),
#    23: ("digital", "Digitalausgang"),
#    24: ("digital", "Steckdosenleiste"),
#    38: ("digital", "Transponderleser"),
#    39: ("digital", "Tastatur"),
#    50: ("analog",  "Temperatursensor"),
#    51: ("digital", "Digitaleingang"),
#    60: ("analog",  "Feuchtesensor"),
#    61: ("digital", "Netzspannungs Messadapter"),
#    62: ("digital", "Sauerstoffsensor"),
#    63: ("analog",  "Analogsensor"),
#    64: ("digital", "Wechselstromzaehler"),
#    70: ("digital", "Zugangssensor (Tuerkontakt)"),
#    71: ("digital", "Erschuetterungssensor"),
#    72: ("digital", "Rauchmelder"),
#    80: ("digital", "LHX 20 RS232"),
# }
# also only one sensor group is supported with this plugin!

Section = dict[str, dict[str, Any]]


def savefloat(f: str) -> float:
    """Tries to cast a string to an float and return it. In case this fails,
    it returns 0.0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0.0 back from this function,
    you can not know whether it is really 0.0 or something went wrong."""
    try:
        return float(f)
    except (TypeError, ValueError):
        return 0.0


def saveint(i: str) -> int:
    """Tries to cast a string to an integer and return it. In case this
    fails, it returns 0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0 back from this function,
    you can not know whether it is really 0 or something went wrong."""
    try:
        return int(i)
    except (TypeError, ValueError):
        return 0


def parse_security_master(string_table: Sequence[StringTable]) -> dict[str, Section]:
    supported_sensors = {
        50: "temp",
        60: "humidity",
        72: "smoke",
    }

    parsed: dict[str, Section] = {"temp": {}, "humidity": {}, "smoke": {}}

    for oid, sensor in string_table[0]:
        if ".5.0" not in str(oid):
            continue

        sensor_num = saveint(oid.split(".")[0])
        service_name = f"{sensor_num} {sensor}"
        num = oid.split(".")[0]
        value, sensor_id, warn_low, warn_high, crit_low, crit_high, alarm = (None,) * 7

        for oid_second, sensor_second in string_table[0]:
            if num + ".1.0" == oid_second:
                sensor_id = saveint(sensor_second[0].encode("utf-8").hex())
            elif num + ".2.0" == oid_second:
                with contextlib.suppress(ValueError):
                    value = float(sensor_second)
            elif num + ".6.0" == oid_second:
                try:
                    alarm = int(sensor_second)
                except ValueError:
                    alarm = -1
            elif num + ".7.0" == oid_second:
                crit_low = saveint(sensor_second) / 1000.0
            elif num + ".8.0" == oid_second:
                warn_low = saveint(sensor_second) / 1000.0
            elif num + ".9.0" == oid_second:
                warn_high = saveint(sensor_second) / 1000.0
            elif num + ".10.0" == oid_second:
                crit_high = saveint(sensor_second) / 1000.0

        if sensor_id in supported_sensors:
            parsed[supported_sensors[sensor_id]][service_name] = {
                "name": sensor,
                "value": value,
                "id": sensor_id,
                "levels_low": (warn_low, crit_low),
                "levels": (warn_high, crit_high),
                "alarm": alarm,
            }

    return parsed


snmp_section_security_master = SNMPSection(
    name="security_master",
    detect=startswith(".1.3.6.1.2.1.1.2.0", "1.3.6.1.4.1.35491"),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.35491.30",
            oids=[OIDEnd(), "3"],
        )
    ],
    parse_function=parse_security_master,
)


def inventory_security_master_sensors(
    parsed: dict[str, Section], sensor_type: str
) -> DiscoveryResult:
    for sensor in parsed[sensor_type]:
        yield Service(item=sensor)


def discover_security_master(section: dict[str, Section]) -> DiscoveryResult:
    yield from inventory_security_master_sensors(section, "smoke")


def check_security_master(item: str, section: dict[str, Section]) -> CheckResult:
    sensor = section["smoke"].get(item)
    if not sensor:
        yield Result(state=State.UNKNOWN, summary="Sensor no found in SNMP output")
        return

    if sensor["alarm"] == 99:
        yield Result(
            state=State.UNKNOWN, summary="Smoke Sensor is not ready or bus element removed"
        )
        return

    value = sensor["value"]
    if value == 0:
        yield Result(state=State.OK, summary="No Smoke")
    elif value == 1:
        yield Result(state=State.CRIT, summary="Smoke detected")
    else:
        yield Result(state=State.UNKNOWN, summary="No Value for Sensor")


check_plugin_security_master = CheckPlugin(
    name="security_master",
    service_name="Sensor %s",
    discovery_function=discover_security_master,
    check_function=check_security_master,
)


def discover_security_master_humidity(section: dict[str, Section]) -> DiscoveryResult:
    yield from inventory_security_master_sensors(section, "humidity")


def check_security_master_humidity(
    item: str, params: Mapping[str, Any], section: dict[str, Section]
) -> CheckResult:
    sensor = section["humidity"].get(item)
    if not sensor:
        yield Result(state=State.UNKNOWN, summary="Sensor not found in SNMP output")
        return

    # params is an immutable Mapping in v2, copy to a mutable dict before mutating
    mutable_params: dict[str, Any] = dict(params)

    if sensor["alarm"] is not None and sensor["alarm"] > -1:
        if not mutable_params.get("levels"):
            mutable_params["levels"] = sensor.get("levels")

        if not mutable_params.get("levels_lower"):
            mutable_params["levels_lower"] = sensor.get("levels_low")

    yield from check_humidity(sensor["value"], mutable_params)


check_plugin_security_master_humidity = CheckPlugin(
    name="security_master_humidity",
    service_name="Sensor %s",
    sections=["security_master"],
    discovery_function=discover_security_master_humidity,
    check_function=check_security_master_humidity,
    check_ruleset_name="humidity",
    check_default_parameters={},
)


def discover_security_master_temp(section: dict[str, Section]) -> DiscoveryResult:
    yield from inventory_security_master_sensors(section, "temp")


def check_security_master_temperature(
    item: str, params: TempParamType, section: dict[str, Section]
) -> CheckResult:
    sensor = section["temp"].get(item)
    if not sensor:
        yield Result(state=State.UNKNOWN, summary="Sensor not found in SNMP output")
        return

    sensor_value = sensor["value"]
    if sensor_value is None:
        yield Result(state=State.UNKNOWN, summary="Sensor value is not in SNMP-WALK")
        return

    yield from check_temperature(
        reading=sensor_value,
        params=params,
        unique_name=item,
        value_store=get_value_store(),
        dev_unit="c",
        dev_levels=sensor["levels"],
        dev_levels_lower=sensor["levels_low"],
    )


check_plugin_security_master_temp = CheckPlugin(
    name="security_master_temp",
    service_name="Sensor %s",
    sections=["security_master"],
    discovery_function=discover_security_master_temp,
    check_function=check_security_master_temperature,
    check_ruleset_name="temperature",
    check_default_parameters={
        "device_levels_handling": "worst",  # this variable is required, in order to define,
        # which status limits are used, also 'levels' are
        # added via WATO, if needed
    },
)
