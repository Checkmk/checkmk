#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.plugins.lib.emc import DETECT_ISILON

check_info = {}


def inventory_isilon_temp(info, is_cpu):
    for sensor_name, _value in info:
        item_name = isilon_temp_item_name(sensor_name)
        if is_cpu == item_name.startswith("CPU"):
            yield item_name, {}


def check_isilon_temp(item, params, info):
    for sensor_name, value in info:
        if item == isilon_temp_item_name(sensor_name):
            return check_temperature(float(value), params, "isilon_%s" % item)
    return None


# Expected sensor names:
# "Temp Until CPU Throttle (CPU 0)"
# "Temp Until CPU Throttle (CPU 1)"
# "Temp Chassis 1 (ISI T1)"
# "Temp Front Panel"
# "Temp Power Supply 1"
# "Temp Power Supply 2"
# "Temp System"
def isilon_temp_item_name(sensor_name):
    if "CPU Throttle" in sensor_name:
        return sensor_name.split("(")[1].split(")")[0]  # "CPU 1"
    return sensor_name[5:]  # "Front Panel"


#   .--Air Temperature-----------------------------------------------------.
#   |                              _    _                                  |
#   |                             / \  (_)_ __                             |
#   |                            / _ \ | | '__|                            |
#   |                           / ___ \| | |                               |
#   |                          /_/   \_\_|_|                               |
#   |                                                                      |
#   |     _____                                   _                        |
#   |    |_   _|__ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |      | |/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |      | |  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      |_|\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   '----------------------------------------------------------------------'


def parse_emc_isilon_temp(string_table: StringTable) -> StringTable:
    return string_table


def discover_emc_isilon_temp(info):
    return inventory_isilon_temp(info, is_cpu=False)


check_info["emc_isilon_temp"] = LegacyCheckDefinition(
    name="emc_isilon_temp",
    parse_function=parse_emc_isilon_temp,
    detect=DETECT_ISILON,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12124.2.54.1",
        oids=["3", "4"],
    ),
    service_name="Temperature %s",
    discovery_function=discover_emc_isilon_temp,
    check_function=check_isilon_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (28.0, 33.0),  # assumed useful levels for ambient / air temperature
    },
)


def discover_emc_isilon_temp_cpu(info):
    return inventory_isilon_temp(info, is_cpu=True)


# .
#   .--CPU Temperature-----------------------------------------------------.
#   |                           ____ ____  _   _                           |
#   |                          / ___|  _ \| | | |                          |
#   |                         | |   | |_) | | | |                          |
#   |                         | |___|  __/| |_| |                          |
#   |                          \____|_|    \___/                           |
#   |                                                                      |
#   |     _____                                   _                        |
#   |    |_   _|__ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |      | |/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |      | |  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      |_|\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   '----------------------------------------------------------------------'

check_info["emc_isilon_temp.cpu"] = LegacyCheckDefinition(
    name="emc_isilon_temp_cpu",
    service_name="Temperature %s",
    sections=["emc_isilon_temp"],
    discovery_function=discover_emc_isilon_temp_cpu,
    check_function=check_isilon_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (75.0, 85.0),  # assumed useful levels for ambient / air temperature
    },
)
