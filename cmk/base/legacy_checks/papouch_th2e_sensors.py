#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.humidity import check_humidity
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    all_of,
    contains,
    OIDEnd,
    SNMPTree,
    startswith,
)

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

    return parsed


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


check_info["papouch_th2e_sensors"] = LegacyCheckDefinition(
    detect=all_of(
        contains(".1.3.6.1.2.1.1.1.0", "th2e"), startswith(".1.3.6.1.2.1.1.2.0", ".0.10.43.6.1.4.1")
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.18248.20.1.2.1.1",
        oids=[OIDEnd(), "1", "2", "3"],
    ),
    parse_function=parse_papouch_th2e_sensors,
    service_name="Temperature %s",
    discovery_function=lambda parsed: inventory_papouch_th2e_sensors_temp(parsed, "temp"),
    check_function=lambda item, params, parsed: check_papouch_th2e_sensors_temp(
        item, params, parsed, "temp"
    ),
    check_ruleset_name="temperature",
)

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
    service_name="Dew point %s",
    sections=["papouch_th2e_sensors"],
    discovery_function=lambda parsed: inventory_papouch_th2e_sensors_temp(parsed, "dewpoint"),
    check_function=lambda item, params, parsed: check_papouch_th2e_sensors_temp(
        item, params, parsed, "dewpoint"
    ),
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

# Suggested by customer
papouch_th2e_sensors_humidity_default_levels = (8, 12, 30, 35)


def inventory_papouch_th2e_sensors_humidity(parsed):
    for item in parsed["humidity"]:
        yield item, papouch_th2e_sensors_humidity_default_levels


def check_papouch_th2e_sensors_humidity(item, params, parsed):
    if item in parsed["humidity"]:
        (state, state_readable), reading, _unit = parsed["humidity"][item]
        yield state, "Status: %s" % state_readable
        yield check_humidity(reading, params)


check_info["papouch_th2e_sensors.humidity"] = LegacyCheckDefinition(
    service_name="Humidity %s",
    sections=["papouch_th2e_sensors"],
    discovery_function=inventory_papouch_th2e_sensors_humidity,
    check_function=check_papouch_th2e_sensors_humidity,
    check_ruleset_name="humidity",
)
