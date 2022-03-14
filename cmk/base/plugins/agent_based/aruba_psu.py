#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from enum import Enum
from typing import Mapping, NamedTuple, Tuple, TypedDict

from .agent_based_api.v1 import (
    all_of,
    check_levels,
    exists,
    get_value_store,
    OIDEnd,
    register,
    render,
    Result,
    Service,
    SNMPTree,
    State,
)
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.aruba import DETECT_2930M
from .utils.temperature import check_temperature, TempParamDict, TempParamType


class PSUWattageParams(TypedDict, total=False):
    levels_abs_upper: Tuple[float, float]
    levels_abs_lower: Tuple[float, float]
    levels_perc_upper: Tuple[float, float]
    levels_perc_lower: Tuple[float, float]


default_psu_temperature_parameters = TempParamDict(
    levels=(50.0, 60.0),
    device_levels_handling="usr",
)

default_psu_wattage_parameters = PSUWattageParams(
    levels_abs_upper=(500.0, 600.0),
    levels_abs_lower=(0.0, 0.0),
    levels_perc_upper=(80.0, 90.0),
    levels_perc_lower=(0.0, 0.0),
)


class PSUState(Enum):
    NotPresent = "1"
    NotPlugged = "2"
    Powered = "3"
    Failed = "4"
    PermFailure = "5"
    Max = "6"


PSUStateMapping = {
    PSUState.NotPresent: State.OK,
    PSUState.NotPlugged: State.OK,
    PSUState.Powered: State.OK,
    PSUState.Failed: State.CRIT,
    PSUState.PermFailure: State.CRIT,
    PSUState.Max: State.OK,
}


class PSU(NamedTuple):
    state: PSUState
    failures: int
    temperature: float
    voltage_info: str
    wattage_curr: int
    wattage_max: int
    last_call: int
    model: str


Section = Mapping[str, PSU]


def parse_aruba_psu(string_table: StringTable) -> Section:
    return {
        f"{entry[8]} {entry[0]}": PSU(
            state=PSUState(entry[1]),
            failures=int(entry[2]),
            temperature=float(entry[3]),
            voltage_info=entry[4],
            wattage_curr=int(entry[5]),
            wattage_max=int(entry[6]),
            last_call=int(entry[7]),
            model=entry[8],
        )
        for entry in string_table
    }


register.snmp_section(
    name="aruba_psu",
    detect=all_of(
        DETECT_2930M,
        exists(".1.3.6.1.4.1.11.2.14.11.5.1.55.1.1.1.*"),
    ),
    parse_function=parse_aruba_psu,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11.2.14.11.5.1.55.1.1.1",
        oids=[
            OIDEnd(),
            "2",  # hpicfDcPower::hpicfPsState
            "3",  # hpicfDcPower::hpicfPsFailures
            "4",  # hpicfDcPower::hpicfPsTemp
            "5",  # hpicfDcPower::hpicfPsVoltageInfo
            "6",  # hpicfDcPower::hpicfPsWattageCur
            "7",  # hpicfDcPower::hpicfPsWattageMax
            "8",  # hpicfDcPower::hpicfPSLastCall
            "9",  # hpicfDcPower::hpicfPsModel
        ],
    ),
)


def discover_aruba_psu(section: Section) -> DiscoveryResult:
    for item, entry in section.items():
        if entry.state in [PSUState.NotPresent, PSUState.NotPlugged]:
            continue
        yield Service(item=item)


#   .--PSU Status----------------------------------------------------------.
#   |           ____  ____  _   _   ____  _        _                       |
#   |          |  _ \/ ___|| | | | / ___|| |_ __ _| |_ _   _ ___           |
#   |          | |_) \___ \| | | | \___ \| __/ _` | __| | | / __|          |
#   |          |  __/ ___) | |_| |  ___) | || (_| | |_| |_| \__ \          |
#   |          |_|   |____/ \___/  |____/ \__\__,_|\__|\__,_|___/          |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_aruba_psu_status(
    item: str,
    section: Section,
) -> CheckResult:
    psu = section.get(item)
    if not psu:
        return

    yield Result(
        state=PSUStateMapping[psu.state],
        summary="PSU Status: %s" % psu.state.name,
    )
    yield Result(
        state=State.OK,
        summary="Uptime: %s" % render.timespan(psu.last_call),
    )


register.check_plugin(
    name="aruba_psu_status",
    sections=["aruba_psu"],
    service_name="PSU Status %s",
    discovery_function=discover_aruba_psu,
    check_function=check_aruba_psu_status,
)

#   .--Temperature---------------------------------------------------------.
#   |     _____                                   _                        |
#   |    |_   _|__ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |      | |/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |      | |  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      |_|\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   '----------------------------------------------------------------------'


def check_aruba_psu_temp(
    item: str,
    params: TempParamType,
    section: Section,
) -> CheckResult:
    psu = section.get(item)
    if not psu:
        return

    yield from check_temperature(
        reading=psu.temperature,
        params=params,
        unique_name=item,
        value_store=get_value_store(),
    )


register.check_plugin(
    name="aruba_psu_temp",
    sections=["aruba_psu"],
    service_name="PSU Temperature %s",
    discovery_function=discover_aruba_psu,
    check_function=check_aruba_psu_temp,
    check_ruleset_name="temperature",
    check_default_parameters=default_psu_temperature_parameters,
)

#   .--Wattage-------------------------------------------------------------.
#   |              __        __    _   _                                   |
#   |              \ \      / /_ _| |_| |_ __ _  __ _  ___                 |
#   |               \ \ /\ / / _` | __| __/ _` |/ _` |/ _ \                |
#   |                \ V  V / (_| | |_| || (_| | (_| |  __/                |
#   |                 \_/\_/ \__,_|\__|\__\__,_|\__, |\___|                |
#   |                                           |___/                      |
#   '----------------------------------------------------------------------'


def check_aruba_psu_wattage(
    item: str,
    params: PSUWattageParams,
    section: Section,
) -> CheckResult:
    if not (psu := section.get(item)):
        return

    yield from check_levels(
        value=psu.wattage_curr,
        levels_upper=params.get("levels_abs_upper"),
        levels_lower=params.get("levels_abs_lower"),
        metric_name="power",
        label="Wattage",
        render_func=lambda x: f"{x:.2f}W",
    )

    yield from check_levels(
        value=psu.wattage_curr / psu.wattage_max * 100.0,
        levels_upper=params.get("levels_perc_upper"),
        levels_lower=params.get("levels_perc_lower"),
        metric_name=None,
        label="Wattage",
        render_func=render.percent,
        notice_only=True,
    )

    yield Result(state=State.OK, summary=f"Maximum Wattage: {psu.wattage_max:.2f}W")
    yield Result(state=State.OK, notice=f"Voltage Info: {psu.voltage_info}")


register.check_plugin(
    name="aruba_psu_wattage",
    sections=["aruba_psu"],
    service_name="PSU Wattage %s",
    discovery_function=discover_aruba_psu,
    check_function=check_aruba_psu_wattage,
    check_ruleset_name="psu_wattage",
    check_default_parameters=default_psu_wattage_parameters,
)
