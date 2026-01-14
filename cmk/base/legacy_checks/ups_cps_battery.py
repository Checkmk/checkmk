#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.plugins.ups.lib import DETECT_UPS_CPS

check_info = {}


def parse_ups_cps_battery(string_table):
    if not string_table:
        return None

    parsed: dict[str, float] = {}

    if string_table[0][0]:
        parsed["capacity"] = int(string_table[0][0])

    # The MIB explicitly declares this to be Celsius
    if string_table[0][1] and string_table[0][1] != "NULL":
        parsed["temperature"] = int(string_table[0][1])

    # A TimeTick is 1/100 s
    if string_table[0][2]:
        parsed["battime"] = float(string_table[0][2]) / 100.0
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


def discover_ups_cps_battery_temp(parsed):
    if "temperature" in parsed:
        yield "Battery", {}


def check_ups_cps_battery_temp(item, params, parsed):
    if "temperature" in parsed:
        return check_temperature(parsed["temperature"], params, "ups_cps_battery_temp")
    return None


check_info["ups_cps_battery.temp"] = LegacyCheckDefinition(
    name="ups_cps_battery_temp",
    service_name="Temperature %s",
    sections=["ups_cps_battery"],
    discovery_function=discover_ups_cps_battery_temp,
    check_function=check_ups_cps_battery_temp,
    check_ruleset_name="temperature",
)

# .
#   .--Capacity------------------------------------------------------------.
#   |                ____                       _ _                        |
#   |               / ___|__ _ _ __   __ _  ___(_) |_ _   _                |
#   |              | |   / _` | '_ \ / _` |/ __| | __| | | |               |
#   |              | |__| (_| | |_) | (_| | (__| | |_| |_| |               |
#   |               \____\__,_| .__/ \__,_|\___|_|\__|\__, |               |
#   |                         |_|                     |___/                |
#   '----------------------------------------------------------------------'


def discover_ups_cps_battery(parsed):
    if "capacity" in parsed:
        yield None, {}


def check_ups_cps_battery(item, params, parsed):
    def check_lower_levels(value, levels):
        if not levels:
            return 0
        warn, crit = levels
        if value < crit:
            return 2
        if value < warn:
            return 1
        return 0

    capacity = parsed["capacity"]
    capacity_params = params["capacity"]
    capacity_status = check_lower_levels(capacity, capacity_params)
    if capacity_status:
        levelstext = " (warn/crit at %d/%d%%)" % capacity_params
    else:
        levelstext = ""
    yield capacity_status, ("Capacity at %d%%" % capacity) + levelstext

    battime = parsed["battime"]
    # WATO rule stores remaining time in minutes
    battime_params = params.get("battime")
    battime_status = check_lower_levels(battime / 60.0, battime_params)
    if battime_status:
        levelstext = " (warn/crit at %d/%d min)" % battime_params
    else:
        levelstext = ""
    yield battime_status, ("%.0f minutes remaining on battery" % (battime / 60.0)) + levelstext


check_info["ups_cps_battery"] = LegacyCheckDefinition(
    name="ups_cps_battery",
    detect=DETECT_UPS_CPS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3808.1.1.1.2.2",
        oids=["1", "3", "4"],
    ),
    parse_function=parse_ups_cps_battery,
    service_name="UPS Battery",
    discovery_function=discover_ups_cps_battery,
    check_function=check_ups_cps_battery,
    check_ruleset_name="ups_capacity",
    check_default_parameters={
        "capacity": (95, 90),
    },
)
