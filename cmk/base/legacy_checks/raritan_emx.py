#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import any_of, equals, SNMPTree
from cmk.base.check_legacy_includes.raritan import (
    check_raritan_sensors_binary,
    raritan_map_state,
    raritan_map_unit,
)
from cmk.base.check_legacy_includes.temperature import check_temperature

check_info = {}


def parse_raritan_emx(string_table):
    raritan_type_map = {
        "0": ("temp", "Air"),
        "1": ("temp", "Water"),
        "2": ("fanspeed", ""),
        "3": ("binary", ""),
        "4": ("valve", ""),
    }
    parsed = {}
    for rack_id, rack_name, sensor_number, value_text, unit, sensor_state in string_table:
        rack_type, rack_type_readable = raritan_type_map[sensor_number]

        extra_name = ""
        if rack_type_readable != "":
            extra_name += " " + rack_type_readable

        rack_name = (f"Rack {rack_id}{extra_name} {rack_name}").replace("DC", "").strip()

        if rack_type in ["binary", ""]:
            rack_value = None
        elif rack_type == "temp":
            rack_value = float(value_text) / 10
        else:
            rack_value = int(value_text)

        parsed[rack_name] = {
            "rack_type": rack_type,
            "rack_unit": raritan_map_unit[unit],
            "rack_value": rack_value,
            "state": raritan_map_state[sensor_state],
        }

    return parsed


def inventory_raritan_emx(parsed, rack_type):
    for rack_name, values in parsed.items():
        if values["rack_type"] == rack_type:
            yield rack_name, None


#   .--temperature---------------------------------------------------------.
#   |      _                                      _                        |
#   |     | |_ ___ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |     | __/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |     | ||  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      \__\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   +----------------------------------------------------------------------+
#   |                             main check                               |
#   '----------------------------------------------------------------------'


def discover_raritan_emx_temp(parsed):
    for rack_name, values in parsed.items():
        if values["rack_type"] == "temp":
            yield rack_name, {}


def check_raritan_emx_temp(item, params, parsed):
    if "Temperature" in item:
        # old style (pre 1.2.8) item name, convert
        item = "Rack " + item.replace(" Temperature", "")
    elif "Fan Speed" in item:
        item = "Rack " + item.replace(" Fan Speed", "")
        return check_raritan_emx_fan(item, params, parsed)
    elif "Door Contact" in item:
        item = "Rack " + item.replace(" Door Contact DC", "")
        return check_raritan_sensors_binary(item, params, parsed)

    if item in parsed:
        rack_value = parsed[item]["rack_value"]
        rack_unit = parsed[item]["rack_unit"]
        state, state_readable = parsed[item]["state"]
        return check_temperature(
            rack_value,
            params,
            item,
            dev_unit=rack_unit,
            dev_status=state,
            dev_status_name=state_readable,
        )
    return None


check_info["raritan_emx"] = LegacyCheckDefinition(
    name="raritan_emx",
    detect=any_of(equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.13742.8")),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.13742.9",
        oids=["1.4.1.1.1", "1.4.1.1.4", "1.4.1.1.2", "2.1.1.3", "1.4.1.1.5", "2.1.1.2"],
    ),
    parse_function=parse_raritan_emx,
    service_name="Temperature %s",
    discovery_function=discover_raritan_emx_temp,
    check_function=check_raritan_emx_temp,
    check_ruleset_name="temperature",
)

# .
#   .--fan-----------------------------------------------------------------.
#   |                            __                                        |
#   |                           / _| __ _ _ __                             |
#   |                          | |_ / _` | '_ \                            |
#   |                          |  _| (_| | | | |                           |
#   |                          |_|  \__,_|_| |_|                           |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_raritan_emx_fan(item, _no_params, parsed):
    if item in parsed:
        fan_speed = parsed[item]["rack_value"]
        fan_unit = parsed[item]["rack_unit"]
        state, state_readable = parsed[item]["state"]
        return state, "Speed: %d%s, status: %s" % (fan_speed, fan_unit, state_readable)
    return None


def discover_raritan_emx_fan(parsed):
    return inventory_raritan_emx(parsed, "fanspeed")


check_info["raritan_emx.fan"] = LegacyCheckDefinition(
    name="raritan_emx_fan",
    service_name="Fan %s",
    sections=["raritan_emx"],
    discovery_function=discover_raritan_emx_fan,
    check_function=check_raritan_emx_fan,
)


def discover_raritan_emx_binary(parsed):
    return inventory_raritan_emx(parsed, "binary")


# .
#   .--binary--------------------------------------------------------------.
#   |                   _     _                                            |
#   |                  | |__ (_)_ __   __ _ _ __ _   _                     |
#   |                  | '_ \| | '_ \ / _` | '__| | | |                    |
#   |                  | |_) | | | | | (_| | |  | |_| |                    |
#   |                  |_.__/|_|_| |_|\__,_|_|   \__, |                    |
#   |                                            |___/                     |
#   '----------------------------------------------------------------------'

check_info["raritan_emx.binary"] = LegacyCheckDefinition(
    name="raritan_emx_binary",
    service_name="Door %s",
    sections=["raritan_emx"],
    discovery_function=discover_raritan_emx_binary,
    check_function=check_raritan_sensors_binary,
)
