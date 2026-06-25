#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamType
from cmk.plugins.ups.lib import DETECT_UPS_CPS

Section = Mapping[str, float]


def parse_ups_cps_battery(string_table: StringTable) -> Section | None:
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


def discover_ups_cps_battery_temp(section: Section | None) -> DiscoveryResult:
    if section is not None and "temperature" in section:
        yield Service(item="Battery")


def check_ups_cps_battery_temp(
    item: str, params: TempParamType, section: Section | None
) -> CheckResult:
    if section is not None and "temperature" in section:
        yield from check_temperature(
            section["temperature"],
            params,
            unique_name="ups_cps_battery_temp",
            value_store=get_value_store(),
        )


check_plugin_ups_cps_battery_temp = CheckPlugin(
    name="ups_cps_battery_temp",
    service_name="Temperature %s",
    sections=["ups_cps_battery"],
    discovery_function=discover_ups_cps_battery_temp,
    check_function=check_ups_cps_battery_temp,
    check_ruleset_name="temperature",
    check_default_parameters={},
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


def discover_ups_cps_battery(section: Section | None) -> DiscoveryResult:
    if section is not None and "capacity" in section:
        yield Service()


def _check_lower_levels(value: float, levels: tuple[int, int] | None) -> State:
    if not levels:
        return State.OK
    warn, crit = levels
    if value < crit:
        return State.CRIT
    if value < warn:
        return State.WARN
    return State.OK


def check_ups_cps_battery(params: Mapping[str, Any], section: Section | None) -> CheckResult:
    if section is None:
        return

    capacity = section["capacity"]
    capacity_params = params["capacity"]
    capacity_status = _check_lower_levels(capacity, capacity_params)
    if capacity_status is not State.OK:
        levelstext = " (warn/crit at %d/%d%%)" % capacity_params
    else:
        levelstext = ""
    yield Result(state=capacity_status, summary=("Capacity at %d%%" % capacity) + levelstext)

    battime = section["battime"]
    # WATO rule stores remaining time in minutes
    battime_params = params.get("battime")
    battime_status = _check_lower_levels(battime / 60.0, battime_params)
    if battime_status is not State.OK and battime_params is not None:
        levelstext = " (warn/crit at %d/%d min)" % battime_params
    else:
        levelstext = ""
    yield Result(
        state=battime_status,
        summary=("%.0f minutes remaining on battery" % (battime / 60.0)) + levelstext,
    )


snmp_section_ups_cps_battery = SimpleSNMPSection(
    name="ups_cps_battery",
    detect=DETECT_UPS_CPS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3808.1.1.1.2.2",
        oids=["1", "3", "4"],
    ),
    parse_function=parse_ups_cps_battery,
)


check_plugin_ups_cps_battery = CheckPlugin(
    name="ups_cps_battery",
    service_name="UPS Battery",
    discovery_function=discover_ups_cps_battery,
    check_function=check_ups_cps_battery,
    check_ruleset_name="ups_capacity",
    check_default_parameters={
        "capacity": (95, 90),
    },
)
