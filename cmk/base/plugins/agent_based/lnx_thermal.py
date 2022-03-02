#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, NamedTuple, Optional, Sequence, Tuple

from .agent_based_api.v1 import get_value_store, register, Service
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.temperature import check_temperature, TempParamDict, TempParamType

# <<<lnx_thermal>>>
# thermal_zone0 enabled acpitz 57000 127000 critical
# thermal_zone1 enabled acpitz 65000 100000 critical 95500 passive

# <<<lnx_thermal>>>
# thermal_zone0 enabled acpitz 47000 90000 critical 79000 passive

# <<<lnx_thermal>>>
# thermal_zone0 enabled acpitz 38000 98000 critical
# thermal_zone1 pkg-temp-0  44000 0 passive 0 passive


class Thermal(NamedTuple):
    enabled: bool
    temperature: float
    passive: Optional[float]
    critical: Optional[float]
    hot: Optional[float]


Section = Mapping[str, Thermal]


def parse_lnx_thermal(string_table: StringTable) -> Section:
    """
    Supported format:
    - Temperature is either the 3rd or 4th element in an info row.
    - After temperature follows pairwise trip point temperature and trip point type.
    - Considered trip points are critical, passive, hot.
    - A known, not considered trip point is active.
    - In case trip point values are 0 or negative (known default values) they are ignored.
    """
    if not string_table:
        return {}

    parsed = {}
    for line in string_table:
        if (thermal_info := _get_thermal_info(line)) is None:
            continue

        thermal_type, unscaled_temp, raw_trip_points = thermal_info

        if thermal_type["type"] == "sunxi-therm":
            # From kernel docs (sysfs-api): unit is milli-degrees
            # but on SunXI the unit is degree (may be a BUG)
            factor = 1.0
        else:
            factor = 1000.0

        trip_points = _get_trip_points(factor, raw_trip_points)

        parsed[_format_item_name(line[0])] = Thermal(
            enabled=_is_enabled(thermal_type),
            temperature=unscaled_temp / factor,
            passive=trip_points.get("passive"),
            critical=trip_points.get("critical"),
            hot=trip_points.get("hot"),
        )

    return parsed


def _get_thermal_info(
    line: Sequence[str],
) -> Optional[Tuple[Mapping[str, str], int, Sequence[str]]]:
    for temp_idx, header in (
        (2, ["name", "type"]),
        (3, ["name", "mode", "type"]),
    ):
        try:
            unscaled_temp = int(line[temp_idx])
            return dict(zip(header, line[:temp_idx])), unscaled_temp, line[temp_idx + 1 :]
        except (IndexError, ValueError):
            pass
    return None


def _format_item_name(raw_name: str) -> str:
    return raw_name.replace("thermal_zone", "Zone ")


def _is_enabled(thermal_type: Mapping) -> bool:
    return thermal_type["mode"] in ["-", "enabled"] if "mode" in thermal_type else True


def _get_trip_points(factor: float, raw_trip_points: Sequence[str]) -> Mapping[str, float]:
    try:
        trip_point_keys = raw_trip_points[1::2]
        trip_point_values = [int(x) / factor for x in raw_trip_points[::2]]  # fixed: true-division
        return {
            tp_name: tp_value
            for tp_name, tp_value in dict(zip(trip_point_keys, trip_point_values)).items()
            if tp_value > 0
        }
    except (IndexError, ValueError):
        return {}


register.agent_section(
    name="lnx_thermal",
    parse_function=parse_lnx_thermal,
)


def discover_lnx_thermal(section: Section) -> DiscoveryResult:
    for item, thermal in section.items():
        if thermal.enabled:
            yield Service(item=item)


def check_lnx_thermal(item: str, params: TempParamType, section: Section) -> CheckResult:
    """
    - Trip points hot and critical are considered for the device crit level. In case both trip
      points are given the lower value is considered for the device crit level.
    - Trip point passive is considered for the device warn level.
    - In case both hot and critical trip points are given the lower trip point value
      is considered for the device crit level.
    - Trip point temperatures are provided via performance data.
    """
    if (data := section.get(item)) is None:
        return

    yield from check_temperature(
        reading=data.temperature,
        params=params,
        dev_levels=_get_levels(data),
        unique_name=item,
        value_store=get_value_store(),
    )


def _get_levels(data: Thermal) -> Optional[Tuple[float, float]]:
    crit = _get_crit_level(data.hot, data.critical)
    warn = data.passive

    if warn is None:
        return None if crit is None else (crit, crit)

    if crit is None:
        return None if warn is None else (warn, warn)

    return (warn, crit)


def _get_crit_level(level0: Optional[float], level1: Optional[float]) -> Optional[float]:
    if level0 is None:
        return level1

    if level1 is None:
        return level0

    return min(level0, level1)


register.check_plugin(
    name="lnx_thermal",
    service_name="Temperature %s",
    discovery_function=discover_lnx_thermal,
    check_function=check_lnx_thermal,
    check_ruleset_name="temperature",
    check_default_parameters=TempParamDict(
        levels=(70.0, 80.0),
        device_levels_handling="devdefault",
    ),
)
