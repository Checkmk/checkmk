#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
from collections.abc import Mapping, Sequence
from typing import Any, NamedTuple

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    render,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamType
from cmk.plugins.lib.ups_modulys import DETECT_UPS_MODULYS


class UPSBattery(NamedTuple):
    health: int
    uptime: int
    remaining_time_in_min: float
    capacity: float
    temperature: float | None


UPSBatterySection = UPSBattery | None


def parse_ups_modulys_battery(string_table: Sequence[StringTable]) -> UPSBatterySection:
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
        remaining_time_in_min = float(sys.maxsize)
    else:
        remaining_time_in_min = float(raw_remaining_time)

    try:
        # Sometimes it could happen that the temperature is not reported
        temperature = float(raw_temperature)
    except ValueError:
        temperature = None

    return UPSBattery(
        health=int(raw_health),
        uptime=int(raw_uptime),
        remaining_time_in_min=remaining_time_in_min,
        capacity=int(raw_capacity),
        temperature=temperature,
    )


snmp_section_ups_modulys_battery = SNMPSection(
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
    detect=DETECT_UPS_MODULYS,
)


def discover_ups_modulys_battery(section: UPSBatterySection) -> DiscoveryResult:
    if section:
        yield Service()


def _check_battery_uptime(uptime: int) -> CheckResult:
    if uptime == 0:
        yield Result(state=State.OK, summary="On mains")
        return
    yield Result(state=State.OK, summary=f"Discharging for {uptime // 60} minutes")


def _check_battery_health(health: int) -> CheckResult:
    if health == 1:
        yield Result(state=State.WARN, summary="Battery health weak")
    if health == 2:
        yield Result(state=State.CRIT, summary="Battery needs to be replaced")


def _check_battery_remaining_time(
    remaining_time: float,
    time_left_params: tuple[float, float],
) -> CheckResult:
    yield from check_levels_v1(
        value=remaining_time,
        levels_lower=time_left_params,
        label="Minutes remaining",
    )


def _check_battery_capacity(
    capacity: float,
    capacity_params: tuple[float, float],
) -> CheckResult:
    yield from check_levels_v1(
        value=capacity,
        levels_lower=capacity_params,
        render_func=render.percent,
        label="Battery capacity at",
    )


def check_ups_modulys_battery(params: Mapping[str, Any], section: UPSBatterySection) -> CheckResult:
    if section is None:
        return

    yield from _check_battery_uptime(section.uptime)

    yield from _check_battery_health(section.health)

    yield from _check_battery_remaining_time(
        section.remaining_time_in_min,
        params["battime"],
    )

    yield from _check_battery_capacity(
        section.capacity,
        params["capacity"],
    )


check_plugin_ups_modulys_battery = CheckPlugin(
    name="ups_modulys_battery",
    discovery_function=discover_ups_modulys_battery,
    check_function=check_ups_modulys_battery,
    service_name="Battery Charge",
    check_default_parameters={"capacity": (95, 90), "battime": (0, 0)},
    check_ruleset_name="ups_capacity",
)


def discover_ups_modulys_battery_temp(section: UPSBatterySection) -> DiscoveryResult:
    if section and section.temperature is not None:
        yield Service(item="Battery")


def check_ups_modulys_battery_temp(
    item: str,
    params: TempParamType,
    section: UPSBatterySection,
) -> CheckResult:
    if section and section.temperature is not None:
        yield from check_temperature(
            reading=section.temperature,
            params=params,
            unique_name=f"ups_modulys_battery_temp_{item}",
            value_store=get_value_store(),
        )


check_plugin_ups_modulys_battery_temp = CheckPlugin(
    name="ups_modulys_battery_temp",
    check_function=check_ups_modulys_battery_temp,
    discovery_function=discover_ups_modulys_battery_temp,
    check_default_parameters={},
    check_ruleset_name="temperature",
    service_name="Temperature %s",
    sections=["ups_modulys_battery"],
)
