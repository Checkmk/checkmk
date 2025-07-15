#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree
from cmk.base.check_legacy_includes.humidity import check_humidity
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.plugins.lib.kentix import DETECT_KENTIX

check_info = {}

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

# parsed:
# {'AlarmManager'   : { 'smoke': 0, 'humidity': 0.0,  'temp': 0.0 , 'leakage':0 },
#  'RZ1SE-INNENRAUM': { 'smoke': 0, 'humidity': 35.9, 'temp': 21.8, 'leakage':1 },
#  'RZ1SE-KLIMA-ALT': { 'smoke': 0, 'humidity': 34.4, 'temp': 22.5, 'leakage':0 },
#  'RZ1SE-KLIMA-NEU': { 'smoke': 0, 'humidity': 47.4, 'temp': 15.9, 'leakage':0 },
#  'RZ1SELI1'       : { 'smoke': 0, 'humidity': 35.6, 'temp': 21.6, 'leakage':0 },
#  'RZ1SERE1'       : { 'smoke': 0, 'humidity': 47.3, 'temp': 16.7, 'leakage':0 },
#  'RZ2AMR001'      : { 'smoke': 0, 'humidity': 36.7, 'temp': 16.6, 'leakage':0 },
#  'RZ2SE-INNENRAUM': { 'smoke': 0, 'humidity': 34.9, 'temp': 18.3, 'leakage':0 },
#  'RZ2SELI1'       : { 'smoke': 0, 'humidity': 41.9, 'temp': 15.1, 'leakage':0 }
# }


def parse_kentix_amp_sensors(string_table):
    info_flattened = []

    for i in range(0, len(string_table[0]), 10):
        info_flattened.append([a[0] for a in string_table[0][i : i + 10]])

    parsed = {}
    for line in info_flattened:
        if line[0] != "":
            parsed[line[0]] = {
                "temp": float(line[1]) / 10,
                "humidity": float(line[2]) / 10,
                "smoke": int(line[4]),
            }
            if line[6] != "":
                parsed[line[0]]["leakage"] = int(line[6])

    return parsed


#   .--temperature---------------------------------------------------------.
#   |      _                                      _                        |
#   |     | |_ ___ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |     | __/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |     | ||  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      \__\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   +----------------------------------------------------------------------+
#   |                            main check                                |
#   '----------------------------------------------------------------------'


def discover_kentix_amp_sensors(section):
    yield from ((key, {}) for key in section)


def check_kentix_amp_sensors(item, params, parsed):
    if item in parsed:
        return check_temperature(parsed[item]["temp"], params, "kentix_amp_sensors_%s" % item)
    return None


check_info["kentix_amp_sensors"] = LegacyCheckDefinition(
    name="kentix_amp_sensors",
    detect=DETECT_KENTIX,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.37954.1",
            oids=["2"],
        )
    ],
    parse_function=parse_kentix_amp_sensors,
    service_name="Temperature %s",
    discovery_function=discover_kentix_amp_sensors,
    check_function=check_kentix_amp_sensors,
    check_ruleset_name="temperature",
)

# .
#   .--humidity------------------------------------------------------------.
#   |              _                     _     _ _ _                       |
#   |             | |__  _   _ _ __ ___ (_) __| (_) |_ _   _               |
#   |             | '_ \| | | | '_ ` _ \| |/ _` | | __| | | |              |
#   |             | | | | |_| | | | | | | | (_| | | |_| |_| |              |
#   |             |_| |_|\__,_|_| |_| |_|_|\__,_|_|\__|\__, |              |
#   |                                                  |___/               |
#   +----------------------------------------------------------------------+


def discover_kentix_amp_sensors_humidity(section):
    yield from ((key, {}) for key in section)


def check_kentix_amp_sensors_humidity(item, params, parsed):
    if item in parsed:
        return check_humidity(parsed[item]["humidity"], params)
    return None


check_info["kentix_amp_sensors.humidity"] = LegacyCheckDefinition(
    name="kentix_amp_sensors_humidity",
    service_name="Humidity %s",
    sections=["kentix_amp_sensors"],
    discovery_function=discover_kentix_amp_sensors_humidity,
    check_function=check_kentix_amp_sensors_humidity,
    check_ruleset_name="humidity",
)


# .
#   .--smoke---------------------------------------------------------------.
#   |                                        _                             |
#   |                    ___ _ __ ___   ___ | | _____                      |
#   |                   / __| '_ ` _ \ / _ \| |/ / _ \                     |
#   |                   \__ \ | | | | | (_) |   <  __/                     |
#   |                   |___/_| |_| |_|\___/|_|\_\___|                     |
#   |                                                                      |
#   +----------------------------------------------------------------------+


def discover_kentix_amp_sensors_smoke(section):
    yield from ((key, {}) for key in section)


def check_kentix_amp_sensors_smoke(item, params, parsed):
    if item in parsed:
        sensor_smoke = parsed[item]["smoke"]

        warn, crit = params["levels"]

        if sensor_smoke >= crit:
            status = 2
        elif sensor_smoke >= warn:
            status = 1
        else:
            status = 0

        infotext = "%.1f%%" % sensor_smoke

        if status > 0:
            infotext += f" (warn/crit at {warn:.1f}%/{crit:.1f}%)"

        perfdata = [("smoke_perc", sensor_smoke, warn, crit, 0, 100)]

        yield status, infotext, perfdata


check_info["kentix_amp_sensors.smoke"] = LegacyCheckDefinition(
    name="kentix_amp_sensors_smoke",
    service_name="Smoke Detector %s",
    sections=["kentix_amp_sensors"],
    discovery_function=discover_kentix_amp_sensors_smoke,
    check_function=check_kentix_amp_sensors_smoke,
    check_ruleset_name="smoke",
    check_default_parameters={"levels": (1.0, 5.0)},
)

# .
#   .--leakage-------------------------------------------------------------.
#   |                  _            _                                      |
#   |                 | | ___  __ _| | ____ _  __ _  ___                   |
#   |                 | |/ _ \/ _` | |/ / _` |/ _` |/ _ \                  |
#   |                 | |  __/ (_| |   < (_| | (_| |  __/                  |
#   |                 |_|\___|\__,_|_|\_\__,_|\__, |\___|                  |
#   |                                         |___/                        |
#   +----------------------------------------------------------------------+


def discover_kentix_amp_sensors_leakage(section):
    yield from ((key, {}) for key in section)


def check_kentix_amp_sensors_leakage(item, params, parsed):
    if item in parsed:
        if parsed[item]["leakage"] > 0:
            return 2, "Alarm or disconnected"
        return 0, "Connected"
    return None


check_info["kentix_amp_sensors.leakage"] = LegacyCheckDefinition(
    name="kentix_amp_sensors_leakage",
    service_name="Leakage %s",
    sections=["kentix_amp_sensors"],
    discovery_function=discover_kentix_amp_sensors_leakage,
    check_function=check_kentix_amp_sensors_leakage,
)

# .
