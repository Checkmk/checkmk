#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from .temperature import check_temperature

# For raritan devices which support the PDU2-, EMD-, or LHX-MIB

#   .--Maps----------------------------------------------------------------.
#   |                       __  __                                         |
#   |                      |  \/  | __ _ _ __  ___                         |
#   |                      | |\/| |/ _` | '_ \/ __|                        |
#   |                      | |  | | (_| | |_) \__ \                        |
#   |                      |_|  |_|\__,_| .__/|___/                        |
#   |                                   |_|                                |
#   +----------------------------------------------------------------------+

# The sensor types with an empty key have no values or levels
# nr. --> (key, additional type human readable)
# SensorTypeEnumeration (EMD-MIB, PDU2-MIB)
# If type_human_readable != '' then it's a more detailed item name.
# Otherwise the information is in the description (e.g. in the
# case of 'Temperature')
raritan_map_type = {
    "1": ("current", "RMS"),
    "2": ("peak", "Peak"),
    "3": ("unbalanced", "Unbalanced"),
    "4": ("voltage", "RMS"),
    "5": ("power", "Active"),
    "6": ("appower", "Apparent"),
    # power factor is defined as the ratio of the real power flowing
    # to the load to the apparent power
    "7": ("power_factor", "Power Factor"),
    "8": ("energy", "Active"),
    "9": ("energy", "Apparent"),
    "10": ("temp", ""),
    "11": ("humidity", ""),
    "12": ("airflow", ""),
    "13": ("pressure_pa", "Air"),
    "14": ("binary", "On/Off"),
    "15": ("binary", "Trip"),
    "16": ("binary", "Vibration"),
    "17": ("binary", "Water Detector"),
    "18": ("binary", "Smoke Detector"),
    "19": ("binary", ""),
    "20": ("binary", "Contact"),
    "21": ("fanspeed", ""),
    "30": ("", "Other"),
    "31": ("", "None"),
}

# SensorUnitsEnumeration (EMD-, PDU2, LHX-MIB)
raritan_map_unit = {
    "-1": "",
    "0": " Other",
    "1": " V",
    "2": " A",
    "3": " W",
    "4": " VA",
    "5": " Wh",
    "6": " VAh",
    # for dev_unit in check_temperature
    "7": "c",
    "8": " hz",
    "9": "%",
    "10": " m/s",
    "11": " Pa",
    # 1 psi = 6894,757293168 Pa
    "12": " psi",
    "13": " g",
    # for dev_unit in check_temperature
    "14": "f",
    "15": " ft",
    "16": " inch",
    "17": " cm",
    "18": " m",
    "19": " RPM",
}

# SensorStateEnumeration (EMD-, PDU2, LHX-MIB)
# nr. --> (check state, state human readable)
raritan_map_state = {
    "-1": (2, "unavailable"),
    "0": (1, "open"),
    "1": (0, "closed"),
    "2": (2, "below lower critical"),
    "3": (1, "below lower warning"),
    "4": (0, "normal"),
    "5": (1, "above upper warning"),
    "6": (2, "above upper critical"),
    "7": (0, "on"),
    "8": (2, "off"),
    "9": (0, "detected"),
    "10": (2, "not detected"),
    "11": (2, "alarmed"),
}

# .
#   .--Functions-----------------------------------------------------------.
#   |             _____                 _   _                              |
#   |            |  ___|   _ _ __   ___| |_(_) ___  _ __  ___              |
#   |            | |_ | | | | '_ \ / __| __| |/ _ \| '_ \/ __|             |
#   |            |  _|| |_| | | | | (__| |_| | (_) | | | \__ \             |
#   |            |_|   \__,_|_| |_|\___|\__|_|\___/|_| |_|___/             |
#   |                                                                      |
#   +----------------------------------------------------------------------+

# snmp_info must be of the form:
# "X.Y.Z",  # IsAvailable -> True/False (1/0)
# "X.Y.Z",  # Number
# "X.Y.Z",  # Name
# "X.Y.Z",  # Type
# "X.Y.Z",  # State
# "X.Y.Z",  # Units
# "X.Y.Z",  # DecimalDigits -> for scaling the values
# "X.Y.Z",  # Value
# "X.Y.Z",  # LowerCriticalThreshold
# "X.Y.Z",  # LowerWarningThreshold
# "X.Y.Z",  # UpperCriticalThreshold
# "X.Y.Z",  # UpperWarningThreshold


def parse_raritan_sensors(info):
    parsed = {}
    for (
        availability,
        sensor_id,
        sensor_name,
        sensor_type,
        sensor_state,
        sensor_unit,
        sensor_exponent,
        sensor_value_str,
        sensor_lower_crit_str,
        sensor_lower_warn_str,
        sensor_upper_crit_str,
        sensor_upper_warn_str,
    ) in info:

        sensor_type, sensor_type_readable = raritan_map_type.get(sensor_type, ("", "Other"))

        extra_name = ""
        if sensor_type_readable != "":
            extra_name += " " + sensor_type_readable

        sensor_name = ("Sensor %s%s %s" % (sensor_id, extra_name, sensor_name)).strip()

        sensor_unit = raritan_map_unit.get(sensor_unit, " Other")

        # binary sensors don't have any values or levels
        if sensor_type in ["binary", ""]:
            sensor_data = []
        else:
            # 1 m/s = 8.11 l/s
            if sensor_unit == " m/s":
                sensor_unit = " l/s"
                factor = 8.11
            else:
                factor = 1
            # if the value is 5 and unitSensorDecimalDigits is 2
            # then actual value is 0.05
            sensor_data = [
                factor * float(x) / pow(10, int(sensor_exponent))
                for x in [
                    sensor_value_str,
                    sensor_lower_crit_str,
                    sensor_lower_warn_str,
                    sensor_upper_crit_str,
                    sensor_upper_warn_str,
                ]
            ]

        parsed[sensor_name] = {
            "availability": availability,
            "state": raritan_map_state.get(sensor_state, (3, "unhandled state")),
            "sensor_type": sensor_type,
            "sensor_data": sensor_data,
            "sensor_unit": sensor_unit,
        }

    return parsed


def inventory_raritan_sensors(parsed, sensor_type):
    inventory = []
    for key, values in parsed.items():
        if values["availability"] == "1" and values["sensor_type"] == sensor_type:
            inventory.append((key, None))

    return inventory


def inventory_raritan_sensors_temp(parsed, sensor_type):
    inventory: list = []
    for key, values in parsed.items():
        if values["availability"] == "1" and values["sensor_type"] == sensor_type:
            inventory.append((key, {}))

    return inventory


def check_raritan_sensors(item, _no_params, parsed):
    if item in parsed:
        state, state_readable = parsed[item]["state"]
        unit = parsed[item]["sensor_unit"]
        reading, crit_lower, warn_lower, crit, warn = parsed[item]["sensor_data"]
        infotext = "%s%s, status: %s" % (reading, unit, state_readable)

        if state > 0 and reading >= warn:
            infotext += " (device warn/crit at %.1f%s/%.1f%s)" % (warn, unit, crit, unit)
        elif state > 0 and reading < warn_lower:
            infotext += " (device warn/crit below %.1f%s/%.1f%s)" % (
                warn_lower,
                unit,
                crit_lower,
                unit,
            )

        return state, infotext, [(parsed[item]["sensor_type"], reading, warn, crit)]
    return None


def check_raritan_sensors_binary(item, _no_params, parsed):
    if item in parsed:
        state, state_readable = parsed[item]["state"]
        return state, "Status: %s" % state_readable
    return None


def check_raritan_sensors_temp(item, params, parsed):
    if item in parsed:
        state, state_readable = parsed[item]["state"]
        reading, crit_lower, warn_lower, crit, warn = parsed[item]["sensor_data"]
        return check_temperature(
            reading,
            params,
            "raritan_sensors_%s" % item,
            dev_unit=parsed[item]["sensor_unit"],
            dev_levels=(warn, crit),
            dev_levels_lower=(warn_lower, crit_lower),
            dev_status=state,
            dev_status_name=state_readable,
        )
    return None
