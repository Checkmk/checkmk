#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, startswith, StringTable
from cmk.base.check_legacy_includes.humidity import check_humidity
from cmk.base.check_legacy_includes.temperature import check_temperature

check_info = {}

#   .--Temperature---------------------------------------------------------.
#   |     _____                                   _                        |
#   |    |_   _|__ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |      | |/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |      | |  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      |_|\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   +----------------------------------------------------------------------+

# ambient temperature levels for a datacenter


def discover_bluenet_sensor_temp(info):
    for sensor_id, sensor_type, _temp, _hum in info:
        # temperature and combined temperature/humidity sensor
        if sensor_type in ("1", "2"):
            if sensor_id == "0":
                descr = "internal"
            else:
                descr = "external %s" % sensor_id
            yield descr, {}


def check_bluenet_sensor_temp(item, params, info):
    for sensor_id, _sensor_type, temp, _hum in info:
        if sensor_id == "0":
            descr = "internal"
        else:
            descr = "external %s" % sensor_id
        if descr == item:
            temperature = float(temp) / 10.0
            return check_temperature(temperature, params, "bluenet_sensor_temp_%s" % item, "c")
    return None


def parse_bluenet_sensor(string_table: StringTable) -> StringTable:
    return string_table


check_info["bluenet_sensor"] = LegacyCheckDefinition(
    name="bluenet_sensor",
    parse_function=parse_bluenet_sensor,
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.21695.1"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.21695.1.10.7.3.1",
        oids=["1", "2", "4", "5"],
    ),
    service_name="Temperature %s",
    discovery_function=discover_bluenet_sensor_temp,
    check_function=check_bluenet_sensor_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (28.0, 35.0),
        "levels_lower": (13.0, 17.0),
    },
)

# .
#   .--Humidity------------------------------------------------------------.
#   |              _   _                 _     _ _ _                       |
#   |             | | | |_   _ _ __ ___ (_) __| (_) |_ _   _               |
#   |             | |_| | | | | '_ ` _ \| |/ _` | | __| | | |              |
#   |             |  _  | |_| | | | | | | | (_| | | |_| |_| |              |
#   |             |_| |_|\__,_|_| |_| |_|_|\__,_|_|\__|\__, |              |
#   |                                                  |___/               |
#   +----------------------------------------------------------------------+

# ambient humidity levels for a datacenter
bluenet_sensor_humidity_default_levels = (35, 40, 60, 65)


def discover_bluenet_sensor_hum(info):
    for sensor_id, sensor_type, _temp, _hum in info:
        # humidity for combined temperature/humidity sensor
        if sensor_type == "2":
            if sensor_id == "0":
                descr = "internal"
            else:
                descr = "external %s" % sensor_id
            yield descr, bluenet_sensor_humidity_default_levels


def check_bluenet_sensor_hum(item, params, info):
    for sensor_id, _sensor_type, _temp, hum in info:
        if sensor_id == "0":
            descr = "internal"
        else:
            descr = "external %s" % sensor_id
        if descr == item:
            humidity = float(hum) / 10.0
            return check_humidity(humidity, params)
    return None


check_info["bluenet_sensor.hum"] = LegacyCheckDefinition(
    name="bluenet_sensor_hum",
    service_name="Humidity %s",
    sections=["bluenet_sensor"],
    discovery_function=discover_bluenet_sensor_hum,
    check_function=check_bluenet_sensor_hum,
    check_ruleset_name="humidity",
)
