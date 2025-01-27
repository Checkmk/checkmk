#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

from cmk.base.check_legacy_includes.humidity import check_humidity
from cmk.base.check_legacy_includes.temperature import check_temperature

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import OIDEnd, SNMPTree, startswith

check_info = {}

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


def parse_security_master(string_table):
    supported_sensors = {
        50: "temp",
        60: "humidity",
        72: "smoke",
    }

    parsed = {"temp": {}, "humidity": {}, "smoke": {}}

    for oid, sensor in string_table[0]:
        if ".5.0" not in str(oid):
            continue

        sensor_num = saveint(oid.split(".")[0])
        service_name = "%d %s" % (sensor_num, sensor)
        num = oid.split(".")[0]
        value, sensor_id, warn_low, warn_high, crit_low, crit_high, alarm = (None,) * 7

        for oid_second, sensor_second in string_table[0]:
            if num + ".1.0" == oid_second:
                sensor_id = saveint(sensor_second[0].encode("utf-8").hex())
            elif num + ".2.0" == oid_second:
                try:
                    value = float(sensor_second)
                except ValueError:
                    pass
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


def inventory_security_master_sensors(parsed, sensor_type):
    for sensor in parsed[sensor_type]:
        yield sensor, {}


def check_security_master(item, _no_params, parsed):
    sensor = parsed["smoke"].get(item)
    if not sensor:
        return 3, "Sensor no found in SNMP output"

    if sensor["alarm"] == 99:
        return 3, "Smoke Sensor is not ready or bus element removed"

    value = sensor["value"]
    if value == 0:
        status, msg = 0, "No Smoke"
    elif value == 1:
        status, msg = 2, "Smoke detected"
    else:
        status, msg = 3, "No Value for Sensor"

    return status, msg


def discover_security_master(parsed):
    return inventory_security_master_sensors(parsed, "smoke")


check_info["security_master"] = LegacyCheckDefinition(
    name="security_master",
    detect=startswith(".1.3.6.1.2.1.1.2.0", "1.3.6.1.4.1.35491"),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.35491.30",
            oids=[OIDEnd(), "3"],
        )
    ],
    parse_function=parse_security_master,
    service_name="Sensor %s",
    discovery_function=discover_security_master,
    check_function=check_security_master,
)

#   .--humidity------------------------------------------------------------.
#   |              _                     _     _ _ _                       |
#   |             | |__  _   _ _ __ ___ (_) __| (_) |_ _   _               |
#   |             | '_ \| | | | '_ ` _ \| |/ _` | | __| | | |              |
#   |             | | | | |_| | | | | | | | (_| | | |_| |_| |              |
#   |             |_| |_|\__,_|_| |_| |_|_|\__,_|_|\__|\__, |              |
#   |                                                  |___/               |
#   '----------------------------------------------------------------------'


def check_security_master_humidity(item, params, parsed):
    sensor = parsed["humidity"].get(item)
    if not sensor:
        return 3, "Sensor not found in SNMP output"

    if sensor["alarm"] is not None and sensor["alarm"] > -1:
        if not params.get("levels"):
            params["levels"] = sensor.get("levels")

        if not params.get("levels_lower"):
            params["levels_lower"] = sensor.get("levels_low")

    return check_humidity(sensor["value"], params)


def discover_security_master_humidity(parsed):
    return inventory_security_master_sensors(parsed, "humidity")


check_info["security_master.humidity"] = LegacyCheckDefinition(
    name="security_master_humidity",
    service_name="Sensor %s",
    sections=["security_master"],
    discovery_function=discover_security_master_humidity,
    check_function=check_security_master_humidity,
    check_ruleset_name="humidity",
)

#   .--temp----------------------------------------------------------------.
#   |                       _                                              |
#   |                      | |_ ___ _ __ ___  _ __                         |
#   |                      | __/ _ \ '_ ` _ \| '_ \                        |
#   |                      | ||  __/ | | | | | |_) |                       |
#   |                       \__\___|_| |_| |_| .__/                        |
#   |                                        |_|                           |
#   '----------------------------------------------------------------------'


def check_security_master_temperature(item, params, parsed):
    sensor = parsed["temp"].get(item)
    if not sensor:
        return 3, "Sensor not found in SNMP output"

    sensor_value = sensor["value"]
    if sensor_value is None:
        return 3, "Sensor value is not in SNMP-WALK"

    return check_temperature(
        reading=sensor_value,
        unique_name=item,
        params=params,
        dev_unit="c",
        dev_levels=sensor["levels"],
        dev_levels_lower=sensor["levels_low"],
    )


def discover_security_master_temp(parsed):
    return inventory_security_master_sensors(parsed, "temp")


check_info["security_master.temp"] = LegacyCheckDefinition(
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
