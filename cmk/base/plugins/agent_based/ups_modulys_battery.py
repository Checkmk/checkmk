#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
from collections.abc import Mapping
from typing import Any, List, NamedTuple

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)

from .agent_based_api.v1 import equals, register, Result, Service, SNMPTree, State


class UPSBattery(NamedTuple):
    health: int
    uptime: int
    remaining_time_in_min: int
    capacity: int
    temperature: int | None


UPSBatterySection = UPSBattery | None


def parse_ups_modulys_battery(string_table: List[StringTable]) -> UPSBatterySection:
    try:
        raw_health, raw_uptime, raw_remaining_time, raw_capacity, raw_temperature = string_table[0][
            0
        ]
    except (IndexError, ValueError):
        return None

    if not raw_uptime or int(raw_uptime) == 0:
        # The "raw_remaining_time" value isn't always reported and we don't know why.
        # One theory is that it will be reported if on battery but we have no data to verify.
        # If the theory holds true, this branch is never taken. If it doesn't then its likely
        # the information is only available on some variants of the device or in some
        # configurations. We can still report useful data based on "capacity"

        # If the "raw_remaining_time" value is 0, it means that the device is not on battery so the it will not run out
        remaining_time_in_min = sys.maxsize
    else:
        remaining_time_in_min = int(raw_remaining_time)

    try:
        # Sometimes it could happen that the temperature is not reported
        temperature = int(raw_temperature)
    except ValueError:
        temperature = None

    return UPSBattery(
        health=int(raw_health),
        uptime=int(raw_uptime),
        remaining_time_in_min=remaining_time_in_min,
        capacity=int(raw_capacity),
        temperature=temperature,
    )


register.snmp_section(
    name="ups_modulys_battery",
    parse_function=parse_ups_modulys_battery,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.2254.2.4.7",
            oids=[
                "1",  # dupsBatteryCondition
                "4",  # dupsSecondsOnBattery
                "5",  # dupsBatteryEstimatedTime
                "8",  # dupsBatteryCapacity
                "9",  # dupsBatteryTemperature
            ],
        )
    ],
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.2254.2.4"),
)


def discover_ups_modulys_battery(section: UPSBatterySection) -> DiscoveryResult:
    if section:
        yield Service()


def check_ups_modulys_battery(
    params: Mapping[str, Any],
    section: UPSBatterySection,
) -> CheckResult:
    warn_left, crit_left = params["battime"]
    warn_perc, crit_perc = params["capacity"]
    if section is None:
        return

    # test 1: on mains or on battery?
    if section.uptime == 0:
        yield Result(state=State.OK, summary="on mains")
    else:
        # we already have configurable levels on remaining capacity which
        # would be superfluous if we reported the discharging state itself
        # as a problem. Thus this reports "OK"
        yield Result(state=State.OK, summary="discharging for %d minutes" % (section.uptime // 60))

    # test 2: battery health
    if section.health == 1:
        yield Result(state=State.WARN, summary="battery health weak")
    elif section.health == 2:
        yield Result(state=State.CRIT, summary="battery needs to be replaced")

    # test 3: remaining capacity
    if section.remaining_time_in_min < crit_left or section.capacity < crit_perc:
        status = State.CRIT
    elif section.remaining_time_in_min < warn_left or section.capacity < warn_perc:
        status = State.WARN
    else:
        status = State.OK

    infotext = "OK"

    if section.remaining_time_in_min < warn_left:
        infotext = "%d minutes remaining (warn/crit at %d/%d min)" % (
            section.remaining_time_in_min,
            warn_left,
            crit_left,
        )

    if section.capacity < warn_perc:
        infotext = "%d percent charged (warn/crit at %d/%d perc)" % (
            section.capacity,
            warn_perc,
            crit_perc,
        )

    yield Result(state=status, summary=infotext)


register.check_plugin(
    name="ups_modulys_battery",
    discovery_function=discover_ups_modulys_battery,
    check_function=check_ups_modulys_battery,
    service_name="Battery Charge",
    check_default_parameters={"capacity": (95, 90), "battime": (0, 0)},
    check_ruleset_name="ups_capacity",
)
