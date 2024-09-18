#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v1.type_defs import StringTable
from cmk.agent_based.v2 import CheckResult, DiscoveryResult, Service, startswith

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

SENSOR_TYPE_NAMES = {
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
    "24": "dewpoint",
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
    "540": "tempHum",
}


SENSOR_STATUS_NAMES = {
    "0": "notconnected",
    "1": "normal",
    "2": "prealert",
    "3": "alert",
    "4": "acknowledged",
    "5": "dismissed",
    "6": "disconnected",
}

SENSOR_DIGITAL_VALUE_NAMES = {
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
    min_threshold: float | None = None  # This is not present for the EnviromuxMicro devices
    max_threshold: float | None = None  # This is not present for the EnviromuxMicro devices


@dataclass
class EnviromuxDigitalSensor:
    value: str
    normal_value: str


@dataclass
class EnviromuxMicroSensor:
    type_: str
    value: float


EnviromuxDigitalSection = Mapping[str, EnviromuxDigitalSensor]
EnviromuxSection = Mapping[str, EnviromuxSensor]


def parse_enviromux(string_table: StringTable) -> EnviromuxSection:
    enviromux_sensors: dict[str, EnviromuxSensor] = {}

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

        sensor_type = SENSOR_TYPE_NAMES.get(line[1], "unknown")
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
            value=SENSOR_DIGITAL_VALUE_NAMES.get(line[2], "unknown"),
            normal_value=SENSOR_DIGITAL_VALUE_NAMES.get(line[3], "unknown"),
        )
        for line in string_table
    }


def parse_enviromux_micro(
    string_table: StringTable,
) -> EnviromuxSection:
    enviromux_micro_sensors: dict[str, EnviromuxSensor] = {}

    for line in string_table:
        try:
            enviromux_micro_sensors.setdefault(
                f"{line[2]} {line[0]}" if "#" not in line[2] else line[2],
                EnviromuxSensor(
                    type_=SENSOR_TYPE_NAMES.get(line[1], "Unknown"),
                    value=float(line[3]) / 10.0,
                ),
            )
        except (IndexError, ValueError):
            continue

    return enviromux_micro_sensors


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


def discover_enviromux_temperature(section: EnviromuxSection) -> DiscoveryResult:
    for item, sensor in section.items():
        if sensor.type_ in ["temperature", "temperatureCombo"]:
            yield Service(item=item)


def discover_enviromux_voltage(section: EnviromuxSection) -> DiscoveryResult:
    for item, sensor in section.items():
        if sensor.type_ == "power":
            yield Service(item=item)


def discover_enviromux_humidity(section: EnviromuxSection) -> DiscoveryResult:
    for item, sensor in section.items():
        if sensor.type_ in ["humidity", "humidityCombo"]:
            yield Service(item=item)


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

DETECT_ENVIROMUX = startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.3699.1.1.11")
DETECT_ENVIROMUX5 = startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.3699.1.1.10")

DETECT_ENVIROMUX_SEMS = startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.3699.1.1.2")

DETECT_ENVIROMUX_MICRO = startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.3699.1.1.12")

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
) -> CheckResult:
    if (sensor := section.get(item)) is None:
        return

    yield from check_temperature(
        reading=sensor.value,
        params=params,
        dev_levels_lower=(
            (sensor.min_threshold, sensor.min_threshold) if sensor.min_threshold else None
        ),
        dev_levels=(sensor.max_threshold, sensor.max_threshold) if sensor.max_threshold else None,
    )


def check_enviromux_voltage(
    item: str,
    params: Mapping[str, Any],
    section: EnviromuxSection,
) -> CheckResult:
    if (sensor := section.get(item)) is None:
        return

    yield from check_levels_v1(
        value=sensor.value,
        metric_name="voltage",
        levels_lower=(
            params["levels_lower"][0],
            params["levels_lower"][1],
        ),
        levels_upper=(
            params["levels"][0],
            params["levels"][1],
        ),
        label="Input Voltage is V",
    )


def check_enviromux_humidity(
    item: str,
    params: Mapping[str, Any],
    section: EnviromuxSection,
) -> CheckResult:
    if (sensor := section.get(item)) is None:
        return

    yield from check_humidity(
        humidity=sensor.value,
        params=params,
    )
