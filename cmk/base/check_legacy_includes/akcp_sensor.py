#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file
from .humidity import check_humidity
from .temperature import check_temperature

#   .--General-------------------------------------------------------------.
#   |                                                  _                   |
#   |                   __ _  ___ _ __   ___ _ __ __ _| |                  |
#   |                  / _` |/ _ \ '_ \ / _ \ '__/ _` | |                  |
#   |                 | (_| |  __/ | | |  __/ | | (_| | |                  |
#   |                  \__, |\___|_| |_|\___|_|  \__,_|_|                  |
#   |                  |___/                                               |
#   +----------------------------------------------------------------------+

# States for sensors with levels as they are defined in SPAGENT-MIB
akcp_sensor_level_states = {
    "1": (2, "no status"),
    "2": (0, "normal"),
    "3": (1, "high warning"),
    "4": (2, "high critical"),
    "5": (1, "low warning"),
    "6": (2, "low critical"),
    "7": (2, "sensor error"),
}


def snmp_scan_akcp_sensor(oid):
    return oid(".1.3.6.1.2.1.1.2.0").startswith(".1.3.6.1.4.1.3854.1") and not oid(
        ".1.3.6.1.4.1.3854.2.*"
    )


def snmp_scan_akcp_exp(oid):
    return oid(".1.3.6.1.2.1.1.2.0").startswith(".1.3.6.1.4.1.3854.1") and oid(
        ".1.3.6.1.4.1.3854.2.*"
    )


def inventory_akcp_sensor_no_params(info):
    for line in info:
        # "1" means online, "2" offline
        if line[-1] == "1":
            yield line[0], None


# .
#   .--Humidity------------------------------------------------------------.
#   |              _                     _     _ _ _                       |
#   |             | |__  _   _ _ __ ___ (_) __| (_) |_ _   _               |
#   |             | '_ \| | | | '_ ` _ \| |/ _` | | __| | | |              |
#   |             | | | | |_| | | | | | | | (_| | | |_| |_| |              |
#   |             |_| |_|\__,_|_| |_| |_|_|\__,_|_|\__|\__, |              |
#   |                                                  |___/               |
#   +----------------------------------------------------------------------+

akcp_humidity_defaultlevels = (30, 35, 60, 65)


def inventory_akcp_humidity(info):
    for description, _percent, _status, online in info:
        if online == "1":
            yield description, "akcp_humidity_defaultlevels"


def check_akcp_humidity(item, params, info):
    for description, percent, status, online in info:
        if description == item:
            # Online is set to "2" if sensor is offline
            if online != "1":
                yield 2, "sensor is offline"

            if status in ["1", "7"]:
                state, state_name = akcp_sensor_level_states[status]
                yield state, "State: %s" % state_name

            if percent:
                yield check_humidity(int(percent), params)


# .
#   .--Temperature---------------------------------------------------------.
#   |      _                                      _                        |
#   |     | |_ ___ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |     | __/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |     | ||  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      \__\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   +----------------------------------------------------------------------+

AKCP_TEMP_CHECK_DEFAULT_PARAMETERS = {
    "levels": (32, 35),
}


def inventory_akcp_sensor_temp(info):
    for line in info:
        # sensorProbeTempOnline or sensorTemperatureGoOffline has to be at last index
        # "1" means online, "2" offline
        if line[-1] == "1":
            yield line[0], {}


def check_akcp_sensor_temp(item, params, info):
    for (
        description,
        degree,
        unit,
        status,
        low_crit,
        low_warn,
        high_warn,
        high_crit,
        degreeraw,
        online,
    ) in info:

        if description == item:
            # Online is set to "2" if sensor is offline
            if online != "1":
                return 2, "sensor is offline"

            if status in ["1", "7"]:
                state, state_name = akcp_sensor_level_states[status]
                return state, "State: %s" % state_name

            # Unit "F" or "0" stands for Fahrenheit and "C" or "1" for Celsius
            if unit.isdigit():
                if unit == "0":
                    unit_normalised = "f"
                else:
                    unit_normalised = "c"
                low_crit, low_warn, high_warn, high_crit = list(
                    map(float, (low_crit, low_warn, high_warn, high_crit))
                )
            else:
                unit_normalised = unit.lower()
                if int(high_crit) > 100:
                    # Devices with "F" or "C" have the levels in degrees * 10
                    low_crit, low_warn, high_warn, high_crit = [
                        float(t) / 10 for t in (low_crit, low_warn, high_warn, high_crit)
                    ]
                else:
                    low_crit, low_warn, high_warn, high_crit = [
                        float(t) for t in (low_crit, low_warn, high_warn, high_crit)
                    ]

            if degreeraw and degreeraw != "0":
                temperature = float(degreeraw) / 10.0
            elif not degree:
                return 3, "Temperature information not found"
            else:
                temperature = float(degree)

            return check_temperature(
                temperature,
                params,
                "akcp_sensor_temp_%s" % item,
                unit_normalised,
                (high_warn, high_crit),
                (low_warn, low_crit),
            )
    return None


# .
#   .--Water & Smoke-------------------------------------------------------.
#   |               _               ___                         _          |
#   |__      ____ _| |_ ___ _ __   ( _ )    ___ _ __ ___   ___ | | _____   |
#   |\ \ /\ / / _` | __/ _ \ '__|  / _ \/\ / __| '_ ` _ \ / _ \| |/ / _ \  |
#   | \ V  V / (_| | ||  __/ |    | (_>  < \__ \ | | | | | (_) |   <  __/  |
#   |  \_/\_/ \__,_|\__\___|_|     \___/\/ |___/_| |_| |_|\___/|_|\_\___|  |
#   |                                                                      |
#   +----------------------------------------------------------------------+


def check_akcp_sensor_relay(item, _no_params, info):
    # States for sensors with relays as they are defined in SPAGENT-MIB
    relay_states = {
        "1": (2, "no status"),
        "2": (0, "normal"),
        "4": (2, "high critical"),
        "6": (2, "low critical"),
        "7": (2, "sensor error"),
        "8": (2, "relay on"),
        "9": (0, "relay off"),
    }

    for description, status, online in info:
        if description == item:
            # Online is set to "2" if sensor is offline
            if online != "1":
                return 2, "sensor is offline"

            state, state_name = relay_states[status]
            return state, "State: %s" % state_name
    return None


# .
#   .--Drycontact----------------------------------------------------------.
#   |             _                            _             _             |
#   |          __| |_ __ _   _  ___ ___  _ __ | |_ __ _  ___| |_           |
#   |         / _` | '__| | | |/ __/ _ \| '_ \| __/ _` |/ __| __|          |
#   |        | (_| | |  | |_| | (_| (_) | | | | || (_| | (__| |_           |
#   |         \__,_|_|   \__, |\___\___/|_| |_|\__\__,_|\___|\__|          |
#   |                    |___/                                             |
#   +----------------------------------------------------------------------+


def check_akcp_sensor_drycontact(item, _no_params, info):
    # States which are not configurable by user as they are defined in SPAGENT-MIB
    states = {
        "1": (2, "no status"),
        "7": (2, "sensor error"),
        "8": (2, "output low"),
        "9": (2, "output high"),
    }

    for line in info:
        if item == line[0]:
            if len(line) == 5:
                status, crit_desc, normal_desc, online = line[1:]
            else:
                status, online = line[1:]
                normal_desc = "Drycontact OK"
                crit_desc = "Drycontact on Error"

            if online != "1":
                infotext = "Sensor is offline"
                state = 2
            elif status == "2":
                state = 0
                infotext = normal_desc
            elif status in ["4", "6"]:
                state = 2
                infotext = crit_desc
            else:
                state, infotext = states[status]

            return state, infotext
    return None
