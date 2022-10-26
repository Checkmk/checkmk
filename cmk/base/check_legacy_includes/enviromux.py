#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from typing import Any, Iterable

from cmk.base.api.agent_based.type_defs import StringTable
from cmk.base.check_api import check_levels

from .humidity import check_humidity
from .temperature import check_temperature, TempParamType

# .
#   .--parse functions-----------------------------------------------------.
#   |                                                                      |
#   |                      _ __   __ _ _ __ ___  ___                       |
#   |                     | '_ \ / _` | '__/ __|/ _ \                      |
#   |                     | |_) | (_| | |  \__ \  __/                      |
#   |                     | .__/ \__,_|_|  |___/\___|                      |
#   |                     |_|                                              |
#   |              __                  _   _                               |
#   |             / _|_   _ _ __   ___| |_(_) ___  _ __  ___               |
#   |            | |_| | | | '_ \ / __| __| |/ _ \| '_ \/ __|              |
#   |            |  _| |_| | | | | (__| |_| | (_) | | | \__ \              |
#   |            |_|  \__,_|_| |_|\___|\__|_|\___/|_| |_|___/              |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'

# TODO: make check_humidity and check_temperature available without magic

sensor_type_names = {
    "0": "undefined",
    "1": "temperature",
    "2": "humidity",
    "3": "power",
    "4": "lowVoltage",
    "5": "current",
    "6": "aclmvVoltage",
    "7": "aclmpVoltage",
    "8": "aclmpPower",
    "9": "water",
    "10": "smoke",
    "11": "vibration",
    "12": "motion",
    "13": "glass",
    "14": "door",
    "15": "keypad",
    "16": "panicButton",
    "17": "keyStation",
    "18": "digInput",
    "22": "light",
    "41": "rmsVoltage",
    "42": "rmsCurrent",
    "43": "activePower",
    "513": "tempHum",
    "32767": "custom",
    "32769": "temperatureCombo",
    "32770": "humidityCombo",
    "540": "tempHum",
}

sensor_type_names_sems_external = {
    "0": "undefined",
    "1": "temperature",
    "2": "humidity",
    "3": "power",
    "4": "lowVoltage",
    "5": "current",
    "6": "aclmvVoltage",
    "7": "aclmpVoltage",
    "8": "aclmpPower",
    "9": "water",
    "10": "smoke",
    "11": "vibration",
    "12": "motion",
    "13": "glass",
    "14": "door",
    "15": "keypad",
    "16": "panicButton",
    "17": "keyStation",
    "18": "dryContact",
    "22": "light",
    "513": "tempHum",
    "32767": "custom",
    "32769": "temperatureCombo",
    "32770": "humidityCombo",
}

sensor_type_names_external = {
    "0": "undefined",
    "1": "temperature",
    "2": "humidity",
    "3": "power",
    "4": "lowVoltage",
    "5": "current",
    "6": "aclmvVoltage",
    "7": "aclmpVoltage",
    "8": "aclmpPower",
    "9": "water",
    "10": "smoke",
    "11": "vibration",
    "12": "motion",
    "13": "glass",
    "14": "door",
    "15": "keypad",
    "16": "panicButton",
    "17": "keyStation",
    "18": "digInput",
    "22": "light",
    "26": "tacDio",
    "36": "acVoltage",
    "37": "acCurrent",
    "38": "dcVoltage",
    "39": "dcCurrent",
    "41": "rmsVoltage",
    "42": "rmsCurrent",
    "43": "activePower",
    "44": "reactivePower",
    "513": "tempHum",
    "32767": "custom",
    "32769": "temperatureCombo",
    "32770": "humidityCombo",
}

sensor_status_names = {
    "0": "notconnected",
    "1": "normal",
    "2": "prealert",
    "3": "alert",
    "4": "acknowledged",
    "5": "dismissed",
    "6": "disconnected",
}

sensor_digital_value_names = {
    "0": "closed",
    "1": "open",
}

ENVIROMUX_CHECK_DEFAULT_PARAMETERS = {
    "levels": (15.0, 16.0),
    "levels_lower": (10.0, 9.0),
}


@dataclass
class EnviromuxSensor:
    type_: str
    value: float
    min_threshold: float
    max_threshold: float


@dataclass
class EnviromuxDigitalSensor:
    value: str
    normal_value: str


EnviromuxDigitalSection = Mapping[str, EnviromuxDigitalSensor]
EnviromuxSection = Mapping[str, EnviromuxSensor]


def parse_enviromux(string_table: StringTable) -> EnviromuxSection:
    enviromux_sensors: MutableMapping[str, EnviromuxSensor] = {}

    for line in string_table:
        sensor_name = f"{line[2]} {line[0]}"

        try:
            sensor_value: float = float(line[3])
            sensor_min: float = float(line[4])
            sensor_max: float = float(line[5])
            # Sensors without value have "Not configured" and can't be float casted
            # skip the parse
        except ValueError:
            continue

        sensor_type = sensor_type_names.get(line[1], "unknown")
        # Observed in the wild: "power" may actually be a voltage
        if sensor_type in ["temperature", "power", "current", "temperatureCombo"]:
            # The MIB specifies that currents, voltages and temperatures have a scaling factor 10
            sensor_value /= 10.0
            sensor_min /= 10.0
            sensor_max /= 10.0

        enviromux_sensors.setdefault(
            sensor_name,
            EnviromuxSensor(
                type_=sensor_type,
                value=sensor_value,
                min_threshold=sensor_min,
                max_threshold=sensor_max,
            ),
        )

    return enviromux_sensors


def parse_enviromux_digital(string_table: StringTable) -> EnviromuxDigitalSection:

    return {
        f"{line[1]} {line[0]}": EnviromuxDigitalSensor(
            value=sensor_digital_value_names.get(line[2], "unknown"),
            normal_value=sensor_digital_value_names.get(line[3], "unknown"),
        )
        for line in string_table
    }


# .
#   .--inventory functions-------------------------------------------------.
#   |             _                      _                                 |
#   |            (_)_ ____   _____ _ __ | |_ ___  _ __ _   _               |
#   |            | | '_ \ \ / / _ \ '_ \| __/ _ \| '__| | | |              |
#   |            | | | | \ V /  __/ | | | || (_) | |  | |_| |              |
#   |            |_|_| |_|\_/ \___|_| |_|\__\___/|_|   \__, |              |
#   |                                                  |___/               |
#   |              __                  _   _                               |
#   |             / _|_   _ _ __   ___| |_(_) ___  _ __  ___               |
#   |            | |_| | | | '_ \ / __| __| |/ _ \| '_ \/ __|              |
#   |            |  _| |_| | | | | (__| |_| | (_) | | | \__ \              |
#   |            |_|  \__,_|_| |_|\___|\__|_|\___/|_| |_|___/              |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def inventory_enviromux_temperature(section: EnviromuxSection) -> Iterable[Any]:
    for item, sensor in section.items():
        if sensor.type_ in ["temperature", "temperatureCombo"]:
            yield item, {}


def inventory_enviromux_voltage(section: EnviromuxSection) -> Iterable[Any]:
    for item, sensor in section.items():
        if sensor.type_ == "power":
            yield item, {}


def inventory_enviromux_humidity(section: EnviromuxSection) -> Iterable[Any]:
    for item, sensor in section.items():
        if sensor.type_ in ["humidity", "humidityCombo"]:
            yield item, {}


# .
#   .--scan functions------------------------------------------------------.
#   |                         __                  _   _                    |
#   |  ___  ___ __ _ _ __    / _|_   _ _ __   ___| |_(_) ___  _ __  ___    |
#   | / __|/ __/ _` | '_ \  | |_| | | | '_ \ / __| __| |/ _ \| '_ \/ __|   |
#   | \__ \ (_| (_| | | | | |  _| |_| | | | | (__| |_| | (_) | | | \__ \   |
#   | |___/\___\__,_|_| |_| |_|  \__,_|_| |_|\___|\__|_|\___/|_| |_|___/   |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def enviromux_scan_function(oid):
    return oid(".1.3.6.1.2.1.1.2.0").startswith(".1.3.6.1.4.1.3699.1.1.11")


def enviromux_sems_scan_function(oid):
    return oid(".1.3.6.1.2.1.1.2.0").startswith(".1.3.6.1.4.1.3699.1.1.2")


# .
#   .--check functions-----------------------------------------------------.
#   |                           _               _                          |
#   |                       ___| |__   ___  ___| | __                      |
#   |                      / __| '_ \ / _ \/ __| |/ /                      |
#   |                     | (__| | | |  __/ (__|   <                       |
#   |                      \___|_| |_|\___|\___|_|\_\                      |
#   |                                                                      |
#   |              __                  _   _                               |
#   |             / _|_   _ _ __   ___| |_(_) ___  _ __  ___               |
#   |            | |_| | | | '_ \ / __| __| |/ _ \| '_ \/ __|              |
#   |            |  _| |_| | | | | (__| |_| | (_) | | | \__ \              |
#   |            |_|  \__,_|_| |_|\___|\__|_|\___/|_| |_|___/              |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_enviromux_temperature(
    item: str,
    params: TempParamType,
    section: EnviromuxSection,
) -> Iterable[Any]:
    if (sensor := section.get(item)) is None:
        return

    yield from check_temperature(
        sensor.value,
        params,
        item,
        dev_levels_lower=(sensor.min_threshold, sensor.min_threshold),
        dev_levels=(sensor.max_threshold, sensor.max_threshold),
    )


def check_enviromux_voltage(
    item: str,
    params: Mapping[str, Any],
    section: EnviromuxSection,
) -> Iterable[Any]:

    if (sensor := section.get(item)) is None:
        return

    yield from check_levels(
        value=sensor.value,
        dsname="voltage",
        params=(
            params["levels"][0],
            params["levels"][1],
            params["levels_lower"][0],
            params["levels_lower"][1],
        ),
        unit="V",
        infoname="Input Voltage is",
    )


def check_enviromux_humidity(
    item: str,
    params: Mapping[str, Any],
    section: EnviromuxSection,
) -> Iterable[Any]:
    if (sensor := section.get(item)) is None:
        return

    yield from check_humidity(
        humidity=sensor.value,
        params=params,
    )
