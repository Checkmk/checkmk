#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, startswith
from cmk.base.check_legacy_includes.humidity import check_humidity
from cmk.base.check_legacy_includes.temperature import check_temperature

check_info = {}

_TYPE_TABLE_IDX = (1, 2, 3, 6, 7, 8, 9, 16, 18, 36, 37, 38, 42)


def parse_wut_webtherm(string_table):
    map_sensor_type = {
        "1": "temp",
        "2": "humid",
        "3": "air_pressure",
    }
    parsed = {}
    for webtherm_type, info in zip(_TYPE_TABLE_IDX, string_table):
        for sensor_id, reading_de, reading_en in info:
            reading_str = reading_en or reading_de.replace(",", ".")
            if not reading_str or "---" in reading_str:
                continue

            # Dependent on webtherm_type we have to determine
            # which sensors are available. Feel free to
            # declare more sensor types here.
            # We have only temperature sensors
            if webtherm_type <= 9:  # TODO: this is just a guess
                parsed[sensor_id] = {
                    "type": "temp",
                    "reading": float(reading_str),
                }
            # Here we have three different types of sensors:
            # 1 = temp, 2 = humid, 3 = air pressure
            else:
                parsed[sensor_id] = {
                    "type": map_sensor_type[sensor_id],
                    "reading": float(reading_str),
                }

    return parsed


#   .--Temperature---------------------------------------------------------.
#   |     _____                                   _                        |
#   |    |_   _|__ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |      | |/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |      | |  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      |_|\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   +----------------------------------------------------------------------+
#   |                             main check                               |
#   '----------------------------------------------------------------------'


def discover_wut_webtherm(parsed):
    return [(sensor_id, {}) for sensor_id, values in parsed.items() if values["type"] == "temp"]


def check_wut_webtherm(item, params, parsed):
    if item in parsed:
        return check_temperature(parsed[item]["reading"], params, "wut_webtherm_%s" % item)
    return None


check_info["wut_webtherm"] = LegacyCheckDefinition(
    name="wut_webtherm",
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.5040.1.2."),
    fetch=[
        SNMPTree(
            base=f".1.3.6.1.4.1.5040.1.2.{idx}.1",
            oids=[
                "2.1.1",  # WebGraph-Thermo-Hygro-Barometer-MIB::wtWebGraphThermoBaroSensorNo
                "3.1.1",  # WebGraph-Thermo-Hygro-Barometer-MIB::wtWebGraphThermoBaroTempValue
                "8.1.1",  # WebGraph-Thermo-Hygro-Barometer-MIB::wtWebGraphThermoBaroTempValuePkt
            ],
        )
        for idx in _TYPE_TABLE_IDX
    ],
    parse_function=parse_wut_webtherm,
    service_name="Temperature %s",
    discovery_function=discover_wut_webtherm,
    check_function=check_wut_webtherm,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (30.0, 35.0),
    },
)

# .
#   .--Air Pressure--------------------------------------------------------.
#   |          _    _        ____                                          |
#   |         / \  (_)_ __  |  _ \ _ __ ___  ___ ___ _   _ _ __ ___        |
#   |        / _ \ | | '__| | |_) | '__/ _ \/ __/ __| | | | '__/ _ \       |
#   |       / ___ \| | |    |  __/| | |  __/\__ \__ \ |_| | | |  __/       |
#   |      /_/   \_\_|_|    |_|   |_|  \___||___/___/\__,_|_|  \___|       |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_wut_webtherm_pressure(parsed):
    return [
        (sensor_id, None)
        for sensor_id, values in parsed.items()
        if values["type"] == "air_pressure"
    ]


def check_wut_webtherm_pressure(item, _no_params, parsed):
    if item in parsed:
        return 0, "%.2f hPa" % parsed[item]["reading"]
    return None


check_info["wut_webtherm.pressure"] = LegacyCheckDefinition(
    name="wut_webtherm_pressure",
    service_name="Pressure %s",
    sections=["wut_webtherm"],
    discovery_function=discover_wut_webtherm_pressure,
    check_function=check_wut_webtherm_pressure,
)

# .
#   .--Humidity------------------------------------------------------------.
#   |              _   _                 _     _ _ _                       |
#   |             | | | |_   _ _ __ ___ (_) __| (_) |_ _   _               |
#   |             | |_| | | | | '_ ` _ \| |/ _` | | __| | | |              |
#   |             |  _  | |_| | | | | | | | (_| | | |_| |_| |              |
#   |             |_| |_|\__,_|_| |_| |_|_|\__,_|_|\__|\__, |              |
#   |                                                  |___/               |
#   '----------------------------------------------------------------------'


def discover_wut_webtherm_humidity(parsed):
    return [(sensor_id, {}) for sensor_id, values in parsed.items() if values["type"] == "humid"]


def check_wut_webtherm_humidity(item, params, parsed):
    if item in parsed:
        return check_humidity(parsed[item]["reading"], params)
    return None


check_info["wut_webtherm.humidity"] = LegacyCheckDefinition(
    name="wut_webtherm_humidity",
    service_name="Humidity %s",
    sections=["wut_webtherm"],
    discovery_function=discover_wut_webtherm_humidity,
    check_function=check_wut_webtherm_humidity,
    check_ruleset_name="humidity",
    check_default_parameters={
        "levels": (60.0, 65.0),
        "levels_lower": (40.0, 35.0),
    },
)

# .
