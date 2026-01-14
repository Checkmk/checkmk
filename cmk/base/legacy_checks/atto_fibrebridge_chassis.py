#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, startswith
from cmk.base.check_legacy_includes.temperature import check_temperature

check_info = {}


def parse_atto_fibrebridge_chassis(string_table):
    if not string_table:
        return None

    parsed = {}

    min_operating_temp = int(string_table[0][0])
    max_operating_temp = int(string_table[0][1])
    chassis_temp = int(string_table[0][2])

    parsed["temperature"] = {
        "dev_levels": (max_operating_temp, max_operating_temp),
        "dev_levels_lower": (min_operating_temp, min_operating_temp),
        "reading": chassis_temp,
    }

    parsed["throughput_status"] = string_table[0][3]

    return parsed


# .
#   .--Temperature---------------------------------------------------------.
#   |     _____                                   _                        |
#   |    |_   _|__ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |      | |/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |      | |  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      |_|\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   '----------------------------------------------------------------------'


def discover_atto_fibrebridge_chassis_temp(parsed):
    return [("Chassis", {})]


def check_atto_fibrebridge_chassis_temp(item, params, parsed):
    return check_temperature(
        params=params, unique_name="atto_fibrebridge_chassis_temp", **parsed["temperature"]
    )


check_info["atto_fibrebridge_chassis.temp"] = LegacyCheckDefinition(
    name="atto_fibrebridge_chassis_temp",
    service_name="Temperature %s",
    sections=["atto_fibrebridge_chassis"],
    discovery_function=discover_atto_fibrebridge_chassis_temp,
    check_function=check_atto_fibrebridge_chassis_temp,
    check_ruleset_name="temperature",
)

# .
#   .--Throughput Status - Main Check--------------------------------------.
#   |       _____ _                           _                 _          |
#   |      |_   _| |__  _ __ ___  _   _  __ _| |__  _ __  _   _| |_        |
#   |        | | | '_ \| '__/ _ \| | | |/ _` | '_ \| '_ \| | | | __|       |
#   |        | | | | | | | | (_) | |_| | (_| | | | | |_) | |_| | |_        |
#   |        |_| |_| |_|_|  \___/ \__,_|\__, |_| |_| .__/ \__,_|\__|       |
#   |                                   |___/      |_|                     |
#   '----------------------------------------------------------------------'


def discover_atto_fibrebridge_chassis(parsed):
    return [(None, None)]


def check_atto_fibrebridge_chassis(_no_item, _no_params, parsed):
    throughput_status = parsed["throughput_status"]
    if throughput_status == "1":
        return 0, "Normal"
    if throughput_status == "2":
        return 1, "Warning"
    return None


check_info["atto_fibrebridge_chassis"] = LegacyCheckDefinition(
    name="atto_fibrebridge_chassis",
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.4547"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.4547.2.3.2",
        oids=["4", "5", "8", "11"],
    ),
    parse_function=parse_atto_fibrebridge_chassis,
    service_name="Throughput Status",
    discovery_function=discover_atto_fibrebridge_chassis,
    check_function=check_atto_fibrebridge_chassis,
)
