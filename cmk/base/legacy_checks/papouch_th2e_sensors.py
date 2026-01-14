#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import all_of, contains, OIDEnd, SNMPTree, startswith
from cmk.base.check_legacy_includes.humidity import check_humidity
from cmk.base.check_legacy_includes.temperature import check_temperature

check_info = {}

# .1.3.6.1.4.1.18248.20.1.2.1.1.1.1 0
# .1.3.6.1.4.1.18248.20.1.2.1.1.1.2 0
# .1.3.6.1.4.1.18248.20.1.2.1.1.1.3 0
# .1.3.6.1.4.1.18248.20.1.2.1.1.2.1 249
# .1.3.6.1.4.1.18248.20.1.2.1.1.2.2 317
# .1.3.6.1.4.1.18248.20.1.2.1.1.2.3 69
# .1.3.6.1.4.1.18248.20.1.2.1.1.3.1 0
# .1.3.6.1.4.1.18248.20.1.2.1.1.3.2 3
# .1.3.6.1.4.1.18248.20.1.2.1.1.3.3 0


def parse_papouch_th2e_sensors(string_table):
    map_sensor_type = {
        "1": "temp",
        "2": "humidity",
        "3": "dewpoint",
    }

    map_units = {
        "0": "c",
        "1": "f",
        "2": "k",
        "3": "percent",
    }

    map_states = {
        "0": (0, "OK"),
        "1": (3, "not available"),
        "2": (1, "over-flow"),
        "3": (1, "under-flow"),
        "4": (2, "error"),
    }

    parsed = {}
    for oidend, state, reading_str, unit in string_table:
        if state != "3":
            sensor_ty = map_sensor_type[oidend]
            sensor_unit = map_units[unit]
            parsed.setdefault(sensor_ty, {})
            parsed[sensor_ty].setdefault(
                "Sensor %s" % oidend,
                (
                    map_states[state],
                    float(reading_str) / 10,
                    sensor_unit,
                ),
            )

    return parsed or None


#   .--temperature---------------------------------------------------------.
#   |      _                                      _                        |
#   |     | |_ ___ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |     | __/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |     | ||  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      \__\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   +----------------------------------------------------------------------+
#   |                               main check                             |
#   '----------------------------------------------------------------------'


def inventory_papouch_th2e_sensors_temp(parsed, what):
    for item in parsed[what]:
        yield item, {}


def check_papouch_th2e_sensors_temp(item, params, parsed, what):
    if item in parsed[what]:
        (state, state_readable), reading, unit = parsed[what][item]
        return check_temperature(
            reading,
            params,
            f"papouch_th2e_sensors_{what}_{item}",
            dev_unit=unit,
            dev_status=state,
            dev_status_name=state_readable,
        )
    return None


def discover_papouch_th2e_sensors(parsed):
    return inventory_papouch_th2e_sensors_temp(parsed, "temp")


def check_papouch_th2e_sensors(item, params, parsed):
    return check_papouch_th2e_sensors_temp(item, params, parsed, "temp")


check_info["papouch_th2e_sensors"] = LegacyCheckDefinition(
    name="papouch_th2e_sensors",
    detect=all_of(
        contains(".1.3.6.1.2.1.1.1.0", "th2e"), startswith(".1.3.6.1.2.1.1.2.0", ".0.10.43.6.1.4.1")
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.18248.20.1.2.1.1",
        oids=[OIDEnd(), "1", "2", "3"],
    ),
    parse_function=parse_papouch_th2e_sensors,
    service_name="Temperature %s",
    discovery_function=discover_papouch_th2e_sensors,
    check_function=check_papouch_th2e_sensors,
    check_ruleset_name="temperature",
)


def discover_papouch_th2e_sensors_dewpoint(parsed):
    return inventory_papouch_th2e_sensors_temp(parsed, "dewpoint")


def check_papouch_th2e_sensors_dewpoint(item, params, parsed):
    return check_papouch_th2e_sensors_temp(item, params, parsed, "dewpoint")


# .
#   .--dew point-----------------------------------------------------------.
#   |                _                             _       _               |
#   |             __| | _____      __  _ __   ___ (_)_ __ | |_             |
#   |            / _` |/ _ \ \ /\ / / | '_ \ / _ \| | '_ \| __|            |
#   |           | (_| |  __/\ V  V /  | |_) | (_) | | | | | |_             |
#   |            \__,_|\___| \_/\_/   | .__/ \___/|_|_| |_|\__|            |
#   |                                 |_|                                  |
#   '----------------------------------------------------------------------'


check_info["papouch_th2e_sensors.dewpoint"] = LegacyCheckDefinition(
    name="papouch_th2e_sensors_dewpoint",
    service_name="Dew point %s",
    sections=["papouch_th2e_sensors"],
    discovery_function=discover_papouch_th2e_sensors_dewpoint,
    check_function=check_papouch_th2e_sensors_dewpoint,
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
#   '----------------------------------------------------------------------'


def discover_papouch_th2e_sensors_humidity(parsed):
    for item in parsed["humidity"]:
        yield item, {}


def check_papouch_th2e_sensors_humidity(item, params, parsed):
    if item in parsed["humidity"]:
        (state, state_readable), reading, _unit = parsed["humidity"][item]
        yield state, "Status: %s" % state_readable
        yield check_humidity(reading, params)


check_info["papouch_th2e_sensors.humidity"] = LegacyCheckDefinition(
    name="papouch_th2e_sensors_humidity",
    service_name="Humidity %s",
    sections=["papouch_th2e_sensors"],
    discovery_function=discover_papouch_th2e_sensors_humidity,
    check_function=check_papouch_th2e_sensors_humidity,
    check_ruleset_name="humidity",
    check_default_parameters={
        "levels": (30.0, 35.0),
        "levels_lower": (12.0, 8.0),
    },
)
