#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import all_of, any_of, contains, OIDEnd, SNMPTree
from cmk.base.check_legacy_includes.temperature import check_temperature

check_info = {}


def parse_hp_psu(string_table):
    parsed = {
        index: {"temp": int(temp), "status": dev_status} for index, dev_status, temp in string_table
    }
    return parsed


#   .--Temperature---------------------------------------------------------.
#   |     _____                                   _                        |
#   |    |_   _|__ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |      | |/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |      | |  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      |_|\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   '----------------------------------------------------------------------'


def discover_hp_psu_temp(parsed):
    for index in parsed:
        yield index, {}


def check_hp_psu_temp(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    # For some status, the device simply reports 0 as a temperature value.
    temp_unknown_status = ["8"]
    if data["status"] in temp_unknown_status and data["temp"] == 0:
        yield 3, "No temperature data available"
    else:
        yield check_temperature(data["temp"], params, item)


check_info["hp_psu.temp"] = LegacyCheckDefinition(
    name="hp_psu_temp",
    service_name="Temperature Power Supply %s",
    sections=["hp_psu"],
    discovery_function=discover_hp_psu_temp,
    check_function=check_hp_psu_temp,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (70.0, 80.0),
    },
)

#   .--Status--------------------------------------------------------------.
#   |                    ____  _        _                                  |
#   |                   / ___|| |_ __ _| |_ _   _ ___                      |
#   |                   \___ \| __/ _` | __| | | / __|                     |
#   |                    ___) | || (_| | |_| |_| \__ \                     |
#   |                   |____/ \__\__,_|\__|\__,_|___/                     |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_hp_psu(parsed):
    for item in parsed:
        yield item, None


def check_hp_psu(item, params, parsed):
    ps_statemap = {
        "1": (2, "Not present"),
        "2": (2, "Not plugged"),
        "3": (0, "Powered"),
        "4": (1, "Failed"),
        "5": (2, "Permanent Failure"),
        "6": (3, "Max"),
        # This value is not specified in the MIB, but has been observed in the wild.
        "8": (2, "Unplugged"),
        "9": (2, "Aux not powered"),
    }

    return ps_statemap.get(parsed[item]["status"], (3, "Unknown status code sent by device"))


check_info["hp_psu"] = LegacyCheckDefinition(
    name="hp_psu",
    detect=all_of(
        contains(".1.3.6.1.2.1.1.1.0", "hp"),
        any_of(
            contains(".1.3.6.1.2.1.1.1.0", "5406rzl2"), contains(".1.3.6.1.2.1.1.1.0", "5412rzl2")
        ),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11.2.14.11.5.1.55.1.1.1",
        oids=[OIDEnd(), "2", "4"],
    ),
    parse_function=parse_hp_psu,
    service_name="Power Supply Status %s",
    discovery_function=discover_hp_psu,
    check_function=check_hp_psu,
)
