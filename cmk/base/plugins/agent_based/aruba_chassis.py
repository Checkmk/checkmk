#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, NamedTuple, Optional

from .agent_based_api.v1 import (
    all_of,
    exists,
    get_value_store,
    OIDEnd,
    register,
    Result,
    Service,
    SNMPTree,
    State,
)
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.aruba import DETECT_2930M
from .utils.temperature import (
    check_temperature,
    render_temp,
    temp_unitsym,
    TempParamDict,
    TempParamType,
    to_celsius,
)


class Chassis(NamedTuple):
    name: str
    curr_temp: float
    max_temp: float
    min_temp: float
    threshold_temp: float
    avg_temp: Optional[float]
    dev_unit: str


Section = Mapping[str, Chassis]

default_chassis_temperature_parameters = TempParamDict(
    levels=(50.0, 60.0),
    device_levels_handling="worst",
)


def _string_to_celsius(temp_str: str) -> float:
    return float(to_celsius(temp_str[:-1], temp_str[-1].lower()))


def parse_aruba_chassis(string_table: StringTable) -> Section:
    return {
        f"{entry[1]} {entry[0]}": Chassis(
            name=entry[1],
            curr_temp=_string_to_celsius(entry[2]),
            max_temp=_string_to_celsius(entry[3]),
            min_temp=_string_to_celsius(entry[4]),
            threshold_temp=_string_to_celsius(entry[5]),
            avg_temp=_string_to_celsius(entry[6]) if entry[6] else None,
            dev_unit=entry[2][-1].lower(),
        )
        for entry in string_table
    }


register.snmp_section(
    name="aruba_chassis_temp",
    detect=all_of(
        DETECT_2930M,
        exists(".1.3.6.1.4.1.11.2.14.11.1.2.8.1.1.*"),
    ),
    parse_function=parse_aruba_chassis,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11.2.14.11.1.2.8.1.1",
        oids=[
            OIDEnd(),
            "2",  # hpicfChassis::hpSystemAirName
            "3",  # hpicfChassis::hpSystemAirCurrentTemp
            "4",  # hpicfChassis::hpSystemAirMaxTemp
            "5",  # hpicfChassis::hpSystemAirMinTemp
            "7",  # hpicfChassis::hpSystemAirThresholdTemp
            "8",  # hpicfChassis::hpSystemAirAvgTemp
        ],
    ),
)


def discover_aruba_chassis_temp(section: Section) -> DiscoveryResult:
    for item in section.keys():
        yield Service(item=item)


def check_aruba_chassis_temp(
    item: str,
    params: TempParamType,
    section: Section,
) -> CheckResult:
    if not (chassis := section.get(item)):
        return

    yield from check_temperature(
        reading=chassis.curr_temp,
        params=params,
        dev_levels=(chassis.threshold_temp, chassis.threshold_temp),
        dev_unit=chassis.dev_unit,
        unique_name=item,
        value_store=get_value_store(),
    )

    yield Result(
        state=State.OK,
        summary=f"Min temperature: {render_temp(chassis.min_temp, chassis.dev_unit) + temp_unitsym[chassis.dev_unit]}",
    )

    yield Result(
        state=State.OK,
        summary=f"Max temperature: {render_temp(chassis.max_temp, chassis.dev_unit) + temp_unitsym[chassis.dev_unit]}",
    )

    if chassis.avg_temp:
        yield Result(
            state=State.OK,
            summary=f"Average temperature: {render_temp(chassis.avg_temp, chassis.dev_unit) + temp_unitsym[chassis.dev_unit]}",
        )


register.check_plugin(
    name="aruba_chassis_temp",
    service_name="Temperature %s",
    discovery_function=discover_aruba_chassis_temp,
    check_function=check_aruba_chassis_temp,
    check_ruleset_name="temperature",
    check_default_parameters=default_chassis_temperature_parameters,
)
