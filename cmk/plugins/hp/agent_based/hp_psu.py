#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import TypedDict

from cmk.agent_based.v2 import (
    all_of,
    any_of,
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    OIDEnd,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamType


class _PSU(TypedDict):
    temp: int
    status: str


Section = Mapping[str, _PSU]


def parse_hp_psu(string_table: StringTable) -> Section:
    return {
        index: _PSU(temp=int(temp), status=dev_status) for index, dev_status, temp in string_table
    }


snmp_section_hp_psu = SimpleSNMPSection(
    name="hp_psu",
    parse_function=parse_hp_psu,
    detect=all_of(
        contains(".1.3.6.1.2.1.1.1.0", "hp"),
        any_of(
            contains(".1.3.6.1.2.1.1.1.0", "5406rzl2"),
            contains(".1.3.6.1.2.1.1.1.0", "5412rzl2"),
        ),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11.2.14.11.5.1.55.1.1.1",
        oids=[OIDEnd(), "2", "4"],
    ),
)


#   .--Temperature---------------------------------------------------------.
#   |     _____                                   _                        |
#   |    |_   _|__ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |      | |/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |      | |  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      |_|\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   '----------------------------------------------------------------------'


def discover_hp_psu_temp(section: Section) -> DiscoveryResult:
    yield from (Service(item=index) for index in section)


def check_hp_psu_temp(item: str, params: TempParamType, section: Section) -> CheckResult:
    if (data := section.get(item)) is None:
        return
    # For some status, the device simply reports 0 as a temperature value.
    if data["status"] == "8" and data["temp"] == 0:
        yield Result(state=State.UNKNOWN, summary="No temperature data available")
        return
    yield from check_temperature(data["temp"], params)


check_plugin_hp_psu_temp = CheckPlugin(
    name="hp_psu_temp",
    service_name="Temperature Power Supply %s",
    sections=["hp_psu"],
    discovery_function=discover_hp_psu_temp,
    check_function=check_hp_psu_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (70.0, 80.0)},
)


#   .--Status--------------------------------------------------------------.
#   |                    ____  _        _                                  |
#   |                   / ___|| |_ __ _| |_ _   _ ___                      |
#   |                   \___ \| __/ _` | __| | | / __|                     |
#   |                    ___) | || (_| | |_| |_| \__ \                     |
#   |                   |____/ \__\__,_|\__|\__,_|___/                     |
#   |                                                                      |
#   '----------------------------------------------------------------------'

_PSU_STATE_MAP: Mapping[str, tuple[State, str]] = {
    "1": (State.CRIT, "Not present"),
    "2": (State.CRIT, "Not plugged"),
    "3": (State.OK, "Powered"),
    "4": (State.WARN, "Failed"),
    "5": (State.CRIT, "Permanent Failure"),
    "6": (State.UNKNOWN, "Max"),
    # This value is not specified in the MIB, but has been observed in the wild.
    "8": (State.CRIT, "Unplugged"),
    "9": (State.CRIT, "Aux not powered"),
}


def discover_hp_psu(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_hp_psu(item: str, section: Section) -> CheckResult:
    if (data := section.get(item)) is None:
        return
    state, summary = _PSU_STATE_MAP.get(
        data["status"], (State.UNKNOWN, "Unknown status code sent by device")
    )
    yield Result(state=state, summary=summary)


check_plugin_hp_psu = CheckPlugin(
    name="hp_psu",
    service_name="Power Supply Status %s",
    discovery_function=discover_hp_psu,
    check_function=check_hp_psu,
)
