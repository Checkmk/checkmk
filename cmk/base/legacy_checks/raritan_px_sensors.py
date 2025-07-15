#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# we use raritan.include but here we have no infomation
# about availability of the sensors
# .1.3.6.1.4.1.13742.4.3.3.1.1.4 4 --> PDU-MIB::sensorID.4
# .1.3.6.1.4.1.13742.4.3.3.1.1.5 5 --> PDU-MIB::sensorID.5
# .1.3.6.1.4.1.13742.4.3.3.1.1.13 13 --> PDU-MIB::sensorID.13
# .1.3.6.1.4.1.13742.4.3.3.1.4.4 Temperature AEA1160298 --> PDU-MIB::externalSensorName.4
# .1.3.6.1.4.1.13742.4.3.3.1.4.5 itbb-pwr15humi5 --> PDU-MIB::externalSensorName.5
# .1.3.6.1.4.1.13742.4.3.3.1.4.13 Temperature AEH0850504 --> PDU-MIB::externalSensorName.13
# .1.3.6.1.4.1.13742.4.3.3.1.2.4 10 --> PDU-MIB::externalSensorType.4
# .1.3.6.1.4.1.13742.4.3.3.1.2.5 11 --> PDU-MIB::externalSensorType.5
# .1.3.6.1.4.1.13742.4.3.3.1.2.13 10 --> PDU-MIB::externalSensorType.13
# .1.3.6.1.4.1.13742.4.3.3.1.40.4 -1 --> PDU-MIB::externalSensorState.4
# .1.3.6.1.4.1.13742.4.3.3.1.40.5 -1 --> PDU-MIB::externalSensorState.5
# .1.3.6.1.4.1.13742.4.3.3.1.40.13 4 --> PDU-MIB::externalSensorState.13
# .1.3.6.1.4.1.13742.4.3.3.1.16.4 -1 --> PDU-MIB::externalSensorUnits.4
# .1.3.6.1.4.1.13742.4.3.3.1.16.5 -1 --> PDU-MIB::externalSensorUnits.5
# .1.3.6.1.4.1.13742.4.3.3.1.16.13 7 --> PDU-MIB::externalSensorUnits.13
# .1.3.6.1.4.1.13742.4.3.3.1.17.4 1 --> PDU-MIB::externalSensorDecimalDigits.4
# .1.3.6.1.4.1.13742.4.3.3.1.17.5 0 --> PDU-MIB::externalSensorDecimalDigits.5
# .1.3.6.1.4.1.13742.4.3.3.1.17.13 1 --> PDU-MIB::externalSensorDecimalDigits.13
# .1.3.6.1.4.1.13742.4.3.3.1.41.4 0 --> PDU-MIB::externalSensorValue.4
# .1.3.6.1.4.1.13742.4.3.3.1.41.5 0 --> PDU-MIB::externalSensorValue.5
# .1.3.6.1.4.1.13742.4.3.3.1.41.13 215 --> PDU-MIB::externalSensorValue.13
# .1.3.6.1.4.1.13742.4.3.3.1.31.4 -1 --> PDU-MIB::externalSensorLowerCriticalThreshold.4
# .1.3.6.1.4.1.13742.4.3.3.1.31.5 -1 --> PDU-MIB::externalSensorLowerCriticalThreshold.5
# .1.3.6.1.4.1.13742.4.3.3.1.31.13 180 --> PDU-MIB::externalSensorLowerCriticalThreshold.13
# .1.3.6.1.4.1.13742.4.3.3.1.32.4 -1 --> PDU-MIB::externalSensorLowerWarningThreshold.4
# .1.3.6.1.4.1.13742.4.3.3.1.32.5 -1 --> PDU-MIB::externalSensorLowerWarningThreshold.5
# .1.3.6.1.4.1.13742.4.3.3.1.32.13 200 --> PDU-MIB::externalSensorLowerWarningThreshold.13
# .1.3.6.1.4.1.13742.4.3.3.1.33.4 -1 --> PDU-MIB::externalSensorUpperCriticalThreshold.4
# .1.3.6.1.4.1.13742.4.3.3.1.33.5 -1 --> PDU-MIB::externalSensorUpperCriticalThreshold.5
# .1.3.6.1.4.1.13742.4.3.3.1.33.13 600 --> PDU-MIB::externalSensorUpperCriticalThreshold.13
# .1.3.6.1.4.1.13742.4.3.3.1.34.4 -1 --> PDU-MIB::externalSensorUpperWarningThreshold.4
# .1.3.6.1.4.1.13742.4.3.3.1.34.5 -1 --> PDU-MIB::externalSensorUpperWarningThreshold.5
# .1.3.6.1.4.1.13742.4.3.3.1.34.13 550 --> PDU-MIB::externalSensorUpperWarningThreshold.13


from cmk.base.check_legacy_includes.raritan import (
    check_raritan_sensors,
    check_raritan_sensors_binary,
    check_raritan_sensors_temp,
    inventory_raritan_sensors,
    inventory_raritan_sensors_temp,
    parse_raritan_sensors,
)

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import equals, SNMPTree

check_info = {}


def parse_raritan_px_sensors(string_table):
    pre_parsed = []
    for (
        sensor_id,
        sensor_name,
        sensor_type,
        sensor_state,
        sensor_unit,
        sensor_factor,
        sensor_value_str,
        sensor_lower_crit_str,
        sensor_lower_warn_str,
        sensor_upper_crit_str,
        sensor_upper_warn_str,
    ) in string_table:
        sensor_name = (
            sensor_name.replace("Temperature", "")
            .replace("Humidity", "")
            .replace("On/Off", "")
            .strip()
        )

        # These raritan devices use the PDU-MIB and have no 'isAvailable' information as used
        # in the 'raritan.include' parse function, thus we take the sensor state instead
        if sensor_state == "-1":
            availability = "0"
        else:
            availability = "1"

        pre_parsed.append(
            [
                availability,
                sensor_id,
                sensor_name,
                sensor_type,
                sensor_state,
                sensor_unit,
                sensor_factor,
                sensor_value_str,
                sensor_lower_crit_str,
                sensor_lower_warn_str,
                sensor_upper_crit_str,
                sensor_upper_warn_str,
            ]
        )

    return parse_raritan_sensors(pre_parsed)


def discover_raritan_px_sensors(parsed):
    return inventory_raritan_sensors_temp(parsed, "temp")


#   .--temperature---------------------------------------------------------.
#   |      _                                      _                        |
#   |     | |_ ___ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |     | __/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |     | ||  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      \__\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   +----------------------------------------------------------------------+
#   |                              main check                              |
#   '----------------------------------------------------------------------'

check_info["raritan_px_sensors"] = LegacyCheckDefinition(
    name="raritan_px_sensors",
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.13742.4"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.13742.4.3.3.1",
        oids=["1", "4", "2", "40", "16", "17", "41", "31", "32", "33", "34"],
    ),
    parse_function=parse_raritan_px_sensors,
    service_name="Temperature %s",
    discovery_function=discover_raritan_px_sensors,
    check_function=check_raritan_sensors_temp,
    check_ruleset_name="temperature",
)


def discover_raritan_px_sensors_humidity(parsed):
    return inventory_raritan_sensors(parsed, "humidity")


# .
#   .--humidity------------------------------------------------------------.
#   |              _                     _     _ _ _                       |
#   |             | |__  _   _ _ __ ___ (_) __| (_) |_ _   _               |
#   |             | '_ \| | | | '_ ` _ \| |/ _` | | __| | | |              |
#   |             | | | | |_| | | | | | | | (_| | | |_| |_| |              |
#   |             |_| |_|\__,_|_| |_| |_|_|\__,_|_|\__|\__, |              |
#   |                                                  |___/               |
#   '----------------------------------------------------------------------'

check_info["raritan_px_sensors.humidity"] = LegacyCheckDefinition(
    name="raritan_px_sensors_humidity",
    service_name="Humidity %s",
    sections=["raritan_px_sensors"],
    discovery_function=discover_raritan_px_sensors_humidity,
    check_function=check_raritan_sensors,
)


def discover_raritan_px_sensors_binary(parsed):
    return inventory_raritan_sensors(parsed, "binary")


# .
#   .--binary--------------------------------------------------------------.
#   |                   _     _                                            |
#   |                  | |__ (_)_ __   __ _ _ __ _   _                     |
#   |                  | '_ \| | '_ \ / _` | '__| | | |                    |
#   |                  | |_) | | | | | (_| | |  | |_| |                    |
#   |                  |_.__/|_|_| |_|\__,_|_|   \__, |                    |
#   |                                            |___/                     |
#   '----------------------------------------------------------------------'

check_info["raritan_px_sensors.binary"] = LegacyCheckDefinition(
    name="raritan_px_sensors_binary",
    service_name="Contact %s",
    sections=["raritan_px_sensors"],
    discovery_function=discover_raritan_px_sensors_binary,
    check_function=check_raritan_sensors_binary,
)
