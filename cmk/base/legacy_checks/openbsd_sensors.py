#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import exists, SNMPTree
from cmk.base.check_legacy_includes.elphase import check_elphase
from cmk.base.check_legacy_includes.fan import check_fan
from cmk.base.check_legacy_includes.temperature import check_temperature

check_info = {}

#   .--example output------------------------------------------------------.
#   |                                               _                      |
#   |                 _____  ____ _ _ __ ___  _ __ | | ___                 |
#   |                / _ \ \/ / _` | '_ ` _ \| '_ \| |/ _ \                |
#   |               |  __/>  < (_| | | | | | | |_) | |  __/                |
#   |                \___/_/\_\__,_|_| |_| |_| .__/|_|\___|                |
#   |                                        |_|                           |
#   |                               _               _                      |
#   |                    ___  _   _| |_ _ __  _   _| |_                    |
#   |                   / _ \| | | | __| '_ \| | | | __|                   |
#   |                  | (_) | |_| | |_| |_) | |_| | |_                    |
#   |                   \___/ \__,_|\__| .__/ \__,_|\__|                   |
#   |                                  |_|                                 |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'

# .1.3.6.1.4.1.30155.2.1.2.1.2.2  sd0
# .1.3.6.1.4.1.30155.2.1.2.1.2.18 temp0
# .1.3.6.1.4.1.30155.2.1.2.1.2.20 temp2
# .1.3.6.1.4.1.30155.2.1.2.1.2.27 fan3
# .1.3.6.1.4.1.30155.2.1.2.1.2.31 fan7
# .1.3.6.1.4.1.30155.2.1.2.1.2.37 Chassis Intru
# .1.3.6.1.4.1.30155.2.1.2.1.2.38 PS1 Status
# .1.3.6.1.4.1.30155.2.1.2.1.2.40 VTT
# .1.3.6.1.4.1.30155.2.1.2.1.2.47 volt9

# .1.3.6.1.4.1.30155.2.1.2.1.3.2  13
# .1.3.6.1.4.1.30155.2.1.2.1.3.18 0
# .1.3.6.1.4.1.30155.2.1.2.1.3.20 0
# .1.3.6.1.4.1.30155.2.1.2.1.3.27 1
# .1.3.6.1.4.1.30155.2.1.2.1.3.31 1
# .1.3.6.1.4.1.30155.2.1.2.1.3.37 9
# .1.3.6.1.4.1.30155.2.1.2.1.3.38 21
# .1.3.6.1.4.1.30155.2.1.2.1.3.40 2
# .1.3.6.1.4.1.30155.2.1.2.1.3.47 2

# .1.3.6.1.4.1.30155.2.1.2.1.5.2  online
# .1.3.6.1.4.1.30155.2.1.2.1.5.18 -273.15
# .1.3.6.1.4.1.30155.2.1.2.1.5.20 56.00
# .1.3.6.1.4.1.30155.2.1.2.1.5.27 4179
# .1.3.6.1.4.1.30155.2.1.2.1.5.31 329
# .1.3.6.1.4.1.30155.2.1.2.1.5.37 off
# .1.3.6.1.4.1.30155.2.1.2.1.5.38 present
# .1.3.6.1.4.1.30155.2.1.2.1.5.40 1.15
# .1.3.6.1.4.1.30155.2.1.2.1.5.47 0.00

# .1.3.6.1.4.1.30155.2.1.2.1.6.2
# .1.3.6.1.4.1.30155.2.1.2.1.6.18 degC
# .1.3.6.1.4.1.30155.2.1.2.1.6.20 degC
# .1.3.6.1.4.1.30155.2.1.2.1.6.27 RPM
# .1.3.6.1.4.1.30155.2.1.2.1.6.31 RPM
# .1.3.6.1.4.1.30155.2.1.2.1.6.37
# .1.3.6.1.4.1.30155.2.1.2.1.6.38
# .1.3.6.1.4.1.30155.2.1.2.1.6.40 V DC
# .1.3.6.1.4.1.30155.2.1.2.1.6.47 V DC

# .1.3.6.1.4.1.30155.2.1.2.1.7.2  1
# .1.3.6.1.4.1.30155.2.1.2.1.7.18 0
# .1.3.6.1.4.1.30155.2.1.2.1.7.20 0
# .1.3.6.1.4.1.30155.2.1.2.1.7.27 0
# .1.3.6.1.4.1.30155.2.1.2.1.7.31 0
# .1.3.6.1.4.1.30155.2.1.2.1.7.37 1
# .1.3.6.1.4.1.30155.2.1.2.1.7.38 1
# .1.3.6.1.4.1.30155.2.1.2.1.7.40 0
# .1.3.6.1.4.1.30155.2.1.2.1.7.47 0

# .
#   .--parse---------------------------------------------------------------.
#   |                                                                      |
#   |                      _ __   __ _ _ __ ___  ___                       |
#   |                     | '_ \ / _` | '__/ __|/ _ \                      |
#   |                     | |_) | (_| | |  \__ \  __/                      |
#   |                     | .__/ \__,_|_|  |___/\___|                      |
#   |                     |_|                                              |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def parse_openbsd_sensors(string_table):
    parsed = {}
    used_descriptions = set()

    def get_item_name(name):
        idx = 0
        new_name = name
        while True:
            if new_name in used_descriptions:
                new_name = "%s/%d" % (name, idx)
                idx += 1
            else:
                used_descriptions.add(new_name)
                break
        return new_name

    openbsd_map_state = {
        "0": 3,
        "1": 0,
        "2": 1,
        "3": 2,
    }

    openbsd_map_type = {
        "0": "temp",
        "1": "fan",
        "2": "voltage",
        "9": "indicator",
        "13": "drive",
        "21": "powersupply",
    }

    for descr, sensortype, value, unit, state in string_table:
        if sensortype not in openbsd_map_type:
            continue
        if (sensortype == "0" and value == "-273.15") or (
            sensortype in ["1", "2"] and float(value) == 0
        ):
            continue

        try:
            value_converted = float(value)
        except ValueError:
            value_converted = value

        item_name = get_item_name(descr)
        parsed[item_name] = {
            "state": openbsd_map_state[state],
            "value": value_converted,
            "unit": unit,
            "type": openbsd_map_type[sensortype],
        }
    return parsed


# .
#   .--inventory-----------------------------------------------------------.
#   |             _                      _                                 |
#   |            (_)_ ____   _____ _ __ | |_ ___  _ __ _   _               |
#   |            | | '_ \ \ / / _ \ '_ \| __/ _ \| '__| | | |              |
#   |            | | | | \ V /  __/ | | | || (_) | |  | |_| |              |
#   |            |_|_| |_|\_/ \___|_| |_|\__\___/|_|   \__, |              |
#   |                                                  |___/               |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def inventory_openbsd_sensors(parsed, sensortype):
    inventory = []
    for key, values in parsed.items():
        if values["type"] == sensortype:
            inventory.append((key, {}))
    return inventory


# .
#   .--temperature---------------------------------------------------------.
#   |      _                                      _                        |
#   |     | |_ ___ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |     | __/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |     | ||  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      \__\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_openbsd_sensors(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    yield check_temperature(data["value"], params, "openbsd_sensors_%s" % item)


def discover_openbsd_sensors(parsed):
    return inventory_openbsd_sensors(parsed, "temp")


check_info["openbsd_sensors"] = LegacyCheckDefinition(
    name="openbsd_sensors",
    detect=exists(".1.3.6.1.4.1.30155.2.1.1.0"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.30155.2.1.2.1",
        oids=["2", "3", "5", "6", "7"],
    ),
    parse_function=parse_openbsd_sensors,
    service_name="Temperature %s",
    discovery_function=discover_openbsd_sensors,
    check_function=check_openbsd_sensors,
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
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_openbsd_sensors_fan(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    yield check_fan(data["value"], params)


def discover_openbsd_sensors_fan(parsed):
    return inventory_openbsd_sensors(parsed, "fan")


check_info["openbsd_sensors.fan"] = LegacyCheckDefinition(
    name="openbsd_sensors_fan",
    service_name="Fan %s",
    sections=["openbsd_sensors"],
    discovery_function=discover_openbsd_sensors_fan,
    check_function=check_openbsd_sensors_fan,
    check_ruleset_name="hw_fans",
    check_default_parameters={
        "lower": (500, 300),
        "upper": (8000, 8400),
    },
)

# .
#   .--voltage-------------------------------------------------------------.
#   |                             _ _                                      |
#   |                 __   _____ | | |_ __ _  __ _  ___                    |
#   |                 \ \ / / _ \| | __/ _` |/ _` |/ _ \                   |
#   |                  \ V / (_) | | || (_| | (_| |  __/                   |
#   |                   \_/ \___/|_|\__\__,_|\__, |\___|                   |
#   |                                        |___/                         |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_openbsd_sensors_voltage(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    item_elphase = {}
    parsed_elphase = {}
    item_elphase["voltage"] = data["value"]
    parsed_elphase[item] = item_elphase

    yield from check_elphase(item, params, parsed_elphase)


def discover_openbsd_sensors_voltage(parsed):
    return inventory_openbsd_sensors(parsed, "voltage")


check_info["openbsd_sensors.voltage"] = LegacyCheckDefinition(
    name="openbsd_sensors_voltage",
    service_name="Voltage Type %s",
    sections=["openbsd_sensors"],
    discovery_function=discover_openbsd_sensors_voltage,
    check_function=check_openbsd_sensors_voltage,
    check_ruleset_name="el_inphase",
)
# .
#   .--powersupply---------------------------------------------------------.
#   |                                                        _             |
#   |     _ __   _____      _____ _ __ ___ _   _ _ __  _ __ | |_   _       |
#   |    | '_ \ / _ \ \ /\ / / _ \ '__/ __| | | | '_ \| '_ \| | | | |      |
#   |    | |_) | (_) \ V  V /  __/ |  \__ \ |_| | |_) | |_) | | |_| |      |
#   |    | .__/ \___/ \_/\_/ \___|_|  |___/\__,_| .__/| .__/|_|\__, |      |
#   |    |_|                                    |_|   |_|      |___/       |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_openbsd_sensors_powersupply(item, _no_params, parsed):
    if not (data := parsed.get(item)):
        return
    yield data["state"], "Status: %s" % data["value"]


def discover_openbsd_sensors_powersupply(parsed):
    return inventory_openbsd_sensors(parsed, "powersupply")


check_info["openbsd_sensors.powersupply"] = LegacyCheckDefinition(
    name="openbsd_sensors_powersupply",
    service_name="Powersupply %s",
    sections=["openbsd_sensors"],
    discovery_function=discover_openbsd_sensors_powersupply,
    check_function=check_openbsd_sensors_powersupply,
)
# .
#   .--indicator-----------------------------------------------------------.
#   |               _           _ _           _                            |
#   |              (_)_ __   __| (_) ___ __ _| |_ ___  _ __                |
#   |              | | '_ \ / _` | |/ __/ _` | __/ _ \| '__|               |
#   |              | | | | | (_| | | (_| (_| | || (_) | |                  |
#   |              |_|_| |_|\__,_|_|\___\__,_|\__\___/|_|                  |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_openbsd_sensors_indicator(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    yield data["state"], "Status: %s" % data["value"]


def discover_openbsd_sensors_indicator(parsed):
    return inventory_openbsd_sensors(parsed, "indicator")


check_info["openbsd_sensors.indicator"] = LegacyCheckDefinition(
    name="openbsd_sensors_indicator",
    service_name="Indicator %s",
    sections=["openbsd_sensors"],
    discovery_function=discover_openbsd_sensors_indicator,
    check_function=check_openbsd_sensors_indicator,
)
# .
#   .--drive---------------------------------------------------------------.
#   |                           _      _                                   |
#   |                        __| |_ __(_)_   _____                         |
#   |                       / _` | '__| \ \ / / _ \                        |
#   |                      | (_| | |  | |\ V /  __/                        |
#   |                       \__,_|_|  |_| \_/ \___|                        |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_openbsd_sensors_drive(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    yield data["state"], "Status: %s" % data["value"]


def discover_openbsd_sensors_drive(parsed):
    return inventory_openbsd_sensors(parsed, "drive")


check_info["openbsd_sensors.drive"] = LegacyCheckDefinition(
    name="openbsd_sensors_drive",
    service_name="Drive %s",
    sections=["openbsd_sensors"],
    discovery_function=discover_openbsd_sensors_drive,
    check_function=check_openbsd_sensors_drive,
)
# .
