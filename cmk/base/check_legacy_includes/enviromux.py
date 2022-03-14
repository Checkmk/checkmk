#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file
from .humidity import check_humidity
from .temperature import check_temperature

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
    "levels": (15, 16),
    "levels_lower": (10, 9),
}


def parse_enviromux(info):
    parsed = {}

    for line in info:
        sensor_descr = line[2]
        sensor_index = line[0]
        item = sensor_descr + " " + sensor_index

        sensor_type = sensor_type_names.get(line[1], "unknown")
        sensor_status = sensor_status_names.get(line[8], "unknown")
        try:
            sensor_value = int(line[5])
            sensor_min = int(line[9])
            sensor_max = int(line[10])
            # Sensors without value have "Not configured" and can't be int casted
            # skip the parse
        except ValueError:
            continue

        # Observed in the wild: "power" may actually be a voltage m(
        if sensor_type in ["temperature", "power", "current"]:
            # The MIB specifies that currents, voltages and temperatures have a scaling factor 10
            sensor_value /= 10.0
            sensor_min /= 10.0
            sensor_max /= 10.0

        parsed[item] = {
            "sensor_type": sensor_type,
            "sensor_status": sensor_status,
            "sensor_value": sensor_value,
            "sensor_min": sensor_min,
            "sensor_max": sensor_max,
            "sensor_unit": line[6],  # e.g. V, C, %
        }

    return parsed


def parse_enviromux_sems_external(info):
    parsed = {}

    for line in info:
        sensor_descr = line[2]
        sensor_index = line[0]
        item = sensor_descr + " " + sensor_index

        sensor_type = sensor_type_names.get(line[1], "unknown")
        sensor_status = sensor_status_names.get(line[8], "unknown")
        # Observed in the wild: "power" may actually be a voltage m(
        if sensor_type in ["temperature", "power", "current"]:
            # The MIB specifies that currents, voltages and temperatures have a scaling factor 10
            sensor_value = int(line[6]) / 10.0
            sensor_min = int(line[10]) / 10.0
            sensor_max = int(line[11]) / 10.0
        else:
            sensor_value = int(line[6])
            sensor_min = int(line[10])
            sensor_max = int(line[11])

        parsed[item] = {
            "sensor_type": sensor_type,
            "sensor_status": sensor_status,
            "sensor_value": sensor_value,
            "sensor_min": sensor_min,
            "sensor_max": sensor_max,
            "sensor_unit": line[6],  # e.g. V, C, %
        }

    return parsed


def parse_enviromux_external(info):
    parsed = {}

    for line in info:
        sensor_descr = line[2]
        sensor_index = line[0]
        item = sensor_descr + " " + sensor_index

        sensor_type = sensor_type_names.get(line[1], "unknown")
        sensor_status = sensor_status_names.get(line[8], "unknown")
        # Observed in the wild: "power" may actually be a voltage m(
        if sensor_type in ["temperature", "power", "current", "temperatureCombo"]:
            # The MIB specifies that currents, voltages and temperatures have a scaling factor 10
            sensor_value = int(line[6]) / 10.0
            sensor_min = int(line[10]) / 10.0
            sensor_max = int(line[11]) / 10.0
        else:
            sensor_value = int(line[6])
            sensor_min = int(line[10])
            sensor_max = int(line[11])

        parsed[item] = {
            "sensor_type": sensor_type,
            "sensor_status": sensor_status,
            "sensor_value": sensor_value,
            "sensor_min": sensor_min,
            "sensor_max": sensor_max,
            "sensor_unit": line[6],  # e.g. V, C, %
        }

    return parsed


def parse_enviromux_digital(info):
    parsed = {}

    for line in info:
        sensor_descr = line[2]
        sensor_index = line[0]
        sensor_normal_value = sensor_digital_value_names.get(line[8], "unknown")
        sensor_value = sensor_digital_value_names.get(line[6], "unknown")
        item = sensor_descr + " " + sensor_index
        sensor_status = sensor_status_names.get(line[7], "unknown")
        parsed[item] = {
            "sensor_status": sensor_status,
            "sensor_value": sensor_value,
            "sensor_normal_value": sensor_normal_value,
        }

    return parsed


def parse_enviromux_sems_digital(info):
    parsed = {}

    for line in info:
        sensor_descr = line[1]
        sensor_index = line[0]
        sensor_normal_value = sensor_digital_value_names.get(line[5], "unknown")
        sensor_value = sensor_digital_value_names.get(line[4], "unknown")
        item = sensor_descr + " " + sensor_index
        sensor_status = sensor_status_names.get(line[6], "unknown")
        parsed[item] = {
            "sensor_status": sensor_status,
            "sensor_value": sensor_value,
            "sensor_normal_value": sensor_normal_value,
        }

    return parsed


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


def inventory_enviromux_temperature(parsed):
    for item, sensor_data in parsed.items():
        if sensor_data["sensor_type"] in ["temperature", "temperatureCombo"]:
            yield item, {}


def inventory_enviromux_voltage(parsed):
    for item, sensor_data in parsed.items():
        if sensor_data["sensor_type"] == "power":
            yield item, {}


def inventory_enviromux_humidity(parsed):
    for item, sensor_data in parsed.items():
        if sensor_data["sensor_type"] in ["humidity", "humidityCombo"]:
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


def check_enviromux_temperature(item, params, parsed):
    dev_levels_lower = (parsed[item]["sensor_min"], parsed[item]["sensor_min"])
    dev_levels = (parsed[item]["sensor_max"], parsed[item]["sensor_max"])
    return check_temperature(
        parsed[item]["sensor_value"],
        params,
        item,
        dev_levels_lower=dev_levels_lower,
        dev_levels=dev_levels,
    )


def check_enviromux_voltage(item, params, parsed):
    sensor_value = parsed[item]["sensor_value"]
    perf = [("voltage", sensor_value)]
    infotext = "Input Voltage is %.1f V" % sensor_value
    min_warn = params["levels_lower"][0]
    min_crit = params["levels_lower"][1]
    max_warn = params["levels"][0]
    max_crit = params["levels"][1]
    levelstext_lower = " (warn/crit below %s/%s)" % (min_warn, min_crit)
    levelstext_upper = " (warn/crit at %s/%s)" % (max_warn, max_crit)
    levelstext = ""
    if sensor_value >= max_crit:
        state = 2
        levelstext = levelstext_upper
    elif sensor_value < min_crit:
        state = 2
        levelstext = levelstext_lower
    elif sensor_value < min_warn:
        state = 1
        levelstext = levelstext_lower
    elif sensor_value >= max_warn:
        state = 1
        levelstext = levelstext_upper
    else:
        state = 0
    if state:
        infotext += levelstext
    return state, infotext, perf


def check_enviromux_humidity(item, params, parsed):
    return check_humidity(parsed[item]["sensor_value"], params)
