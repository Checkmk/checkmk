#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from enum import Enum
from typing import Mapping, NamedTuple, Tuple

from .agent_based_api.v1 import all_of, exists, OIDEnd, register, Result, Service, SNMPTree, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.aruba import DETECT_2930M


class FanType(Enum):
    Unknown = "0"
    MM = "1"
    FM = "2"
    IM = "3"
    PS = "4"
    Rollup = "5"
    Maxtype = "6"


class FanState(Enum):
    Failed = "0"
    Removed = "1"
    Off = "2"
    Underspeed = "3"
    Overspeed = "4"
    OK = "5"
    MaxState = "6"


FanStateMapping = {
    FanState.Failed: State.CRIT,
    FanState.Removed: State.WARN,
    FanState.Off: State.WARN,
    FanState.Underspeed: State.WARN,
    FanState.Overspeed: State.WARN,
    FanState.OK: State.OK,
    FanState.MaxState: State.OK,
}


class Fan(NamedTuple):
    tray: int
    type: FanType
    state: FanState
    failures: int


Section = Mapping[str, Fan]

TemperatureParams = Tuple[float, float]


def parse_aruba_fans(string_table: StringTable) -> Section:
    return {
        f"{int(entry[0]):06d}": Fan(
            tray=int(entry[1]),
            type=FanType(entry[2]),
            state=FanState(entry[3]),
            failures=int(entry[4]),
        )
        for entry in string_table
    }


register.snmp_section(
    name="aruba_fan_status",
    detect=all_of(
        DETECT_2930M,
        exists(".1.3.6.1.4.1.11.2.14.11.5.1.54.2.1.1.*"),
    ),
    parse_function=parse_aruba_fans,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11.2.14.11.5.1.54.2.1.1",
        oids=[
            OIDEnd(),
            "2",  # hpicfDcFan::hpicfFanTray
            "3",  # hpicfDcFan::hpicfFanType
            "4",  # hpicfDcFan::hpicfFanState
            "6",  # hpicfDcFan::hpicfFanNumFailures
        ],
    ),
)


def discover_aruba_fan_status(section: Section) -> DiscoveryResult:
    for item in section.keys():
        yield Service(item=item)


def check_aruba_fan_status(
    item: str,
    section: Section,
) -> CheckResult:
    fan = section.get(item)
    if not fan:
        return

    yield Result(
        state=FanStateMapping[fan.state],
        summary=f"Fan Status: {fan.state.name}",
    )
    yield Result(state=State.OK, summary=f"Type: {fan.type.name}")
    yield Result(state=State.OK, summary=f"Tray: {fan.tray}")
    if fan.failures > 0:
        yield Result(state=State.OK, summary=f"Failures: {fan.failures}")


register.check_plugin(
    name="aruba_fan_status",
    service_name="Fan Status %s",
    discovery_function=discover_aruba_fan_status,
    check_function=check_aruba_fan_status,
)
