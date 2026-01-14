#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import any_of, OIDEnd, SNMPTree, startswith
from cmk.base.check_legacy_includes.temperature import check_temperature

check_info = {}

# very odd and confusing example outputs:

# version 3.0.0
# .1.3.6.1.4.1.21239.5.1.1.2.0 3.0.0
# .1.3.6.1.4.1.21239.5.1.1.7.0 1
# .1.3.6.1.4.1.21239.5.1.2.1.3.1 Data Center 1
# .1.3.6.1.4.1.21239.5.1.2.1.5.1 1
# .1.3.6.1.4.1.21239.5.1.2.1.4.1 "91 54 06 9D C9 54 06 9D E9 C9 06 9D BD 9B 06 9D "
# .1.3.6.1.4.1.21239.5.1.2.1.6.1 199
# .1.3.6.1.4.1.21239.5.1.2.1.7.1 36
# .1.3.6.1.4.1.21239.5.1.2.1.8.1 44
#
# version 3.2.0
# .1.3.6.1.4.1.21239.5.1.1.2.0 3.2.0
# .1.3.6.1.4.1.21239.5.1.1.7.0 1
# .1.3.6.1.4.1.21239.5.1.2.1.1.1 1
# .1.3.6.1.4.1.21239.5.1.2.1.2.1 41D88039003580C3
# .1.3.6.1.4.1.21239.5.1.2.1.3.1 RSGLDN Watchdog 15
# .1.3.6.1.4.1.21239.5.1.2.1.4.1 1
# .1.3.6.1.4.1.21239.5.1.2.1.5.1 173
# .1.3.6.1.4.1.21239.5.1.2.1.6.1 46
# .1.3.6.1.4.1.21239.5.1.2.1.7.1 56


def _translate_availability(availability):
    return {
        "0": (2, "unavailable"),
        "1": (0, "available"),
        "2": (1, "partially unavailable"),
    }[availability]


def _parse_legacy_line(line, temp_unit):
    """
    >>> [i for i in _parse_legacy_line(['1', 'blah', '2CD', '1', '30', '20', '8'], 'C')]
    [('general', {'Watchdog 1': {'descr': 'blah', 'availability': (0, 'available')}}), ('temp', {'Temperature 1': ('30', 'C')}), ('humidity', {'Humidity 1': '20'}), ('dew', {'Dew point 1': ('8', 'C')})]
    """
    sensor_id = line[0]
    yield (
        "general",
        {
            "Watchdog %s" % sensor_id: {
                "descr": line[1],
                "availability": _translate_availability(line[3]),
            },
        },
    )
    yield "temp", {"Temperature %s" % sensor_id: (line[4], temp_unit)}
    yield "humidity", {"Humidity %s" % sensor_id: line[5]}
    yield "dew", {"Dew point %s" % sensor_id: (line[6], temp_unit)}


def _parse_line(line, temp_unit):
    """
    >>> [i for i in _parse_line(['1', 'blah', '1', '30', '20', '8'], 'C')]
    [('general', {'Watchdog 1': {'descr': 'blah', 'availability': (0, 'available')}}), ('temp', {'Temperature 1': ('30', 'C')}), ('humidity', {'Humidity 1': '20'}), ('dew', {'Dew point 1': ('8', 'C')})]
    """
    sensor_id = line[0]
    yield (
        "general",
        {
            "Watchdog %s" % sensor_id: {
                "descr": line[1],
                "availability": _translate_availability(line[2]),
            },
        },
    )
    yield "temp", {"Temperature %s" % sensor_id: (line[3], temp_unit)}
    yield "humidity", {"Humidity %s" % sensor_id: line[4]}
    yield "dew", {"Dew point %s" % sensor_id: (line[5], temp_unit)}


def parse_watchdog_sensors(string_table):
    parsed = {}

    general, data = string_table
    if not general:
        return parsed

    temp_unit = {
        "1": "C",
        "0": "F",
        "": "C",
    }[general[0][1]]

    version = int(general[0][0].replace(".", ""))

    if version <= 300:
        line_parser = _parse_legacy_line
    else:
        line_parser = _parse_line

    for line in data:
        for sensor_type, parsed_line in line_parser(line, temp_unit):
            parsed.setdefault(sensor_type, {}).update(parsed_line)

    return parsed


# .
#   .--general-------------------------------------------------------------.
#   |                                                  _                   |
#   |                   __ _  ___ _ __   ___ _ __ __ _| |                  |
#   |                  / _` |/ _ \ '_ \ / _ \ '__/ _` | |                  |
#   |                 | (_| |  __/ | | |  __/ | | (_| | |                  |
#   |                  \__, |\___|_| |_|\___|_|  \__,_|_|                  |
#   |                  |___/                                               |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_watchdog_sensors(parsed):
    for key in parsed.get("general", {}):
        yield (key, {})


def check_watchdog_sensors(item, params, parsed):
    data = parsed.get("general", {}).get(item)

    if not data:
        return

    descr = data["descr"]
    state, state_readable = data["availability"]

    yield state, state_readable

    if not descr == "":
        yield 0, "Location: %s" % descr


check_info["watchdog_sensors"] = LegacyCheckDefinition(
    name="watchdog_sensors",
    detect=any_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.21239.5.1"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.21239.42.1"),
    ),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.21239.5.1.1",
            oids=["2", "7"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.21239.5.1.2.1",
            oids=[OIDEnd(), "3", "4", "5", "6", "7", "8"],
        ),
    ],
    parse_function=parse_watchdog_sensors,
    service_name="%s",
    discovery_function=discover_watchdog_sensors,
    check_function=check_watchdog_sensors,
)

# .
#   .--temp----------------------------------------------------------------.
#   |                       _                                              |
#   |                      | |_ ___ _ __ ___  _ __                         |
#   |                      | __/ _ \ '_ ` _ \| '_ \                        |
#   |                      | ||  __/ | | | | | |_) |                       |
#   |                       \__\___|_| |_| |_| .__/                        |
#   |                                        |_|                           |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_watchdog_sensors_temp(parsed):
    for key in parsed.get("temp", {}):
        yield (key, {})


def check_watchdog_sensors_temp(item, params, parsed):
    data = parsed.get("temp", {}).get(item)

    if not data:
        return None

    temperature_str, unit = data
    return check_temperature(
        float(temperature_str) / 10.0,
        params,
        "check_watchdog_sensors.%s" % item,
        dev_unit=unit.lower(),
    )


check_info["watchdog_sensors.temp"] = LegacyCheckDefinition(
    name="watchdog_sensors_temp",
    service_name="%s ",
    sections=["watchdog_sensors"],
    discovery_function=discover_watchdog_sensors_temp,
    check_function=check_watchdog_sensors_temp,
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
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_watchdog_sensors_humidity(parsed):
    for key in parsed.get("humidity", {}):
        yield (key, {})


def check_watchdog_sensors_humidity(item, params, parsed):
    data = parsed.get("humidity", {}).get(item)

    if not data:
        return

    humidity = int(data)
    warn, crit = params["levels"]
    warn_lower, crit_lower = params["levels_lower"]

    yield 0, "%.1f%%" % humidity, [("humidity", humidity, warn, crit)]

    if humidity >= crit:
        yield 2, f"warn/crit at {warn}/{crit}"
    elif humidity <= crit_lower:
        yield 2, f"warn/crit at {warn}/{crit}"
    elif humidity >= warn:
        yield 1, f"warn/crit below {warn}/{crit}"
    elif humidity <= warn_lower:
        yield 1, f"warn/crit below {warn}/{crit}"


check_info["watchdog_sensors.humidity"] = LegacyCheckDefinition(
    name="watchdog_sensors_humidity",
    service_name="%s",
    sections=["watchdog_sensors"],
    discovery_function=discover_watchdog_sensors_humidity,
    check_function=check_watchdog_sensors_humidity,
    check_ruleset_name="humidity",
    check_default_parameters={
        "levels": (50.0, 55.0),
        "levels_lower": (10.0, 15.0),
    },
)

# .
#   .--dew-----------------------------------------------------------------.
#   |                             _                                        |
#   |                          __| | _____      __                         |
#   |                         / _` |/ _ \ \ /\ / /                         |
#   |                        | (_| |  __/\ V  V /                          |
#   |                         \__,_|\___| \_/\_/                           |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_watchdog_sensors_dew(parsed):
    for key in parsed.get("dew", {}):
        yield (key, {})


def check_watchdog_sensors_dew(item, params, parsed):
    data = parsed.get("dew", {}).get(item)

    if not data:
        return

    dew = float(data[0]) / 10.0
    unit = data[1]
    if unit == "F":
        dew = 5.0 / 9.0 * (dew - 32)
    yield check_temperature(dew, params, "check_watchdog_sensors.%s" % item)


check_info["watchdog_sensors.dew"] = LegacyCheckDefinition(
    name="watchdog_sensors_dew",
    service_name="%s",
    sections=["watchdog_sensors"],
    discovery_function=discover_watchdog_sensors_dew,
    check_function=check_watchdog_sensors_dew,
    check_ruleset_name="temperature",
)
