#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


import re
from collections.abc import Mapping

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.base.check_legacy_includes.humidity import check_humidity
from cmk.base.check_legacy_includes.temperature import check_temperature

check_info = {}

# Example output from agent:

# <<<allnet_ip_sensoric:sep(59)>>>
# sensor0.alarm0;0
# sensor0.all4000_typ;0
# sensor0.function;1
# sensor0.limit_high;50.00
# sensor0.limit_low;10.00
# sensor0.maximum;28.56
# sensor0.minimum;27.50
# sensor0.name;Temperatur intern
# sensor0.value_float;27.50
# sensor0.value_int;2750
# sensor0.value_string;27.50
# sensor1.alarm1;0
# sensor1.all4000_typ;0
# sensor1.function;3
# sensor1.limit_high;50.00
# sensor1.limit_low;-0.50
# sensor1.maximum;0.00
# sensor1.minimum;2048000.00
# sensor1.name;ADC 0
# sensor1.value_float;0.00
# sensor1.value_int;0
# sensor1.value_string;0.00
# [...]
# sensor9.alarm9;1
# sensor9.all4000_typ;101
# sensor9.function;12
# sensor9.limit_high;85.00
# sensor9.limit_low;10.00
# sensor9.maximum;100.00
# sensor9.minimum;2048000.02
# sensor9.name;USV Spannung
# sensor9.value_float;100.00
# sensor9.value_int;100
# sensor9.value_string;100
# system.alarmcount;4
# system.date;30.06.2014
# system.devicename;all5000
# system.devicetype;ALL5000
# system.sys;114854
# system.time;16:08:48


def allnet_ip_sensoric_compose_item(sensor_id, sensor):
    sensor_id = re.sub("sensor", "", sensor_id)
    return f"{sensor['name']} Sensor {sensor_id}" if "name" in sensor else f"Sensor {sensor_id}"


def _match_function_or_unit(
    sensor_data: Mapping[str, str], function: str, unit: str | None = None
) -> bool:
    return sensor_data.get("function") == function or (
        unit is not None and sensor_data.get("unit") == unit
    )


#   .--el. tension---------------------------------------------------------.
#   |                  _     _                 _                           |
#   |              ___| |   | |_ ___ _ __  ___(_) ___  _ __                |
#   |             / _ \ |   | __/ _ \ '_ \/ __| |/ _ \| '_ \               |
#   |            |  __/ |_  | ||  __/ | | \__ \ | (_) | | | |              |
#   |             \___|_(_)  \__\___|_| |_|___/_|\___/|_| |_|              |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_allnet_ip_sensoric_tension(parsed):
    return [
        (allnet_ip_sensoric_compose_item(sensor, sensor_data), None)
        for sensor, sensor_data in parsed.items()
        if _match_function_or_unit(sensor_data, "12")
    ]


def check_allnet_ip_sensoric_tension(item, _no_params, parsed):
    sensor_id = "sensor" + re.sub(".+Sensor ", "", item)

    if sensor_id not in parsed:
        return

    value = float(parsed[sensor_id]["value_float"])

    perfdata = [("tension", value, None, None, 0, 100)]

    yield 0 if value == 0 else 2, "%d%% of the normal level" % value, perfdata


check_info["allnet_ip_sensoric.tension"] = LegacyCheckDefinition(
    name="allnet_ip_sensoric_tension",
    # section already migrated!
    service_name="Electric Tension %s",
    sections=["allnet_ip_sensoric"],
    discovery_function=discover_allnet_ip_sensoric_tension,
    check_function=check_allnet_ip_sensoric_tension,
)

# .
#   .--temp----------------------------------------------------------------.
#   |                       _                                              |
#   |                      | |_ ___ _ __ ___  _ __                         |
#   |                      | __/ _ \ '_ ` _ \| '_ \                        |
#   |                      | ||  __/ | | | | | |_) |                       |
#   |                       \__\___|_| |_| |_| .__/                        |
#   |                                        |_|                           |
#   '----------------------------------------------------------------------'


def discover_allnet_ip_sensoric_temp(parsed):
    return [
        (allnet_ip_sensoric_compose_item(sensor, sensor_data), {})
        for sensor, sensor_data in parsed.items()
        if _match_function_or_unit(sensor_data, "1", "°C")
    ]


def check_allnet_ip_sensoric_temp(item, params, parsed):
    sensor_id = "sensor" + re.sub(".+Sensor ", "", item)

    if sensor_id not in parsed:
        return

    temp = float(parsed[sensor_id]["value_float"])

    yield check_temperature(temp, params, "allnet_ip_sensoric_temp_%s" % item)


check_info["allnet_ip_sensoric.temp"] = LegacyCheckDefinition(
    name="allnet_ip_sensoric_temp",
    # section already migrated!
    service_name="Temperature %s",
    sections=["allnet_ip_sensoric"],
    discovery_function=discover_allnet_ip_sensoric_temp,
    check_function=check_allnet_ip_sensoric_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (35.0, 40.0)},
)

# .
#   .--humidity------------------------------------------------------------.
#   |              _                     _     _ _ _                       |
#   |             | |__  _   _ _ __ ___ (_) __| (_) |_ _   _               |
#   |             | '_ \| | | | '_ ` _ \| |/ _` | | __| | | |              |
#   |             | | | | |_| | | | | | | | (_| | | |_| |_| |              |
#   |             |_| |_|\__,_|_| |_| |_|_|\__,_|_|\__|\__, |              |
#   |                                                  |___/               |
#   '----------------------------------------------------------------------'


def discover_allnet_ip_sensoric_humidity(parsed):
    return [
        (allnet_ip_sensoric_compose_item(sensor, sensor_data), {})
        for sensor, sensor_data in parsed.items()
        if _match_function_or_unit(sensor_data, "2", "%")
    ]


def check_allnet_ip_sensoric_humidity(item, params, parsed):
    sensor_id = "sensor" + re.sub(".+Sensor ", "", item)
    if sensor_id not in parsed:
        return

    yield check_humidity(float(parsed[sensor_id]["value_float"]), params)


check_info["allnet_ip_sensoric.humidity"] = LegacyCheckDefinition(
    name="allnet_ip_sensoric_humidity",
    # section already migrated!
    service_name="Humidity %s",
    sections=["allnet_ip_sensoric"],
    discovery_function=discover_allnet_ip_sensoric_humidity,
    check_function=check_allnet_ip_sensoric_humidity,
    check_ruleset_name="humidity",
    check_default_parameters={
        "levels": (60.0, 65.0),
        "levels_lower": (40.0, 35.0),
    },
)

# .
#   .--pressure------------------------------------------------------------.
#   |                                                                      |
#   |               _ __  _ __ ___  ___ ___ _   _ _ __ ___                 |
#   |              | '_ \| '__/ _ \/ __/ __| | | | '__/ _ \                |
#   |              | |_) | | |  __/\__ \__ \ |_| | | |  __/                |
#   |              | .__/|_|  \___||___/___/\__,_|_|  \___|                |
#   |              |_|                                                     |
#   '----------------------------------------------------------------------'


def discover_allnet_ip_sensoric_pressure(parsed):
    return [
        (allnet_ip_sensoric_compose_item(sensor, sensor_data), None)
        for sensor, sensor_data in parsed.items()
        if _match_function_or_unit(sensor_data, "16", "hpa")
    ]


def check_allnet_ip_sensoric_pressure(item, _no_params, parsed):
    sensor_id = "sensor" + re.sub(".+Sensor ", "", item)

    if sensor_id not in parsed:
        return

    pressure = float(parsed[sensor_id]["value_float"]) / 1000

    perfdata = [("pressure", str(pressure) + "bars", None, None, 0)]

    yield 0, "%0.5f bar" % pressure, perfdata


check_info["allnet_ip_sensoric.pressure"] = LegacyCheckDefinition(
    name="allnet_ip_sensoric_pressure",
    # section already migrated!
    service_name="Pressure %s",
    sections=["allnet_ip_sensoric"],
    discovery_function=discover_allnet_ip_sensoric_pressure,
    check_function=check_allnet_ip_sensoric_pressure,
)

# .
