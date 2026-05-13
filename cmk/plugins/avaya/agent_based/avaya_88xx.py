#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import NamedTuple

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
from cmk.plugins.avaya.lib import DETECT_AVAYA
from cmk.plugins.lib.temperature import check_temperature, TempParamType


class Section(NamedTuple):
    fanstate: list[str]
    temp: list[str]


_FAN_STATE_MAP: dict[str, tuple[State, str]] = {
    "1": (State.UNKNOWN, "Reported Unknown"),
    "2": (State.OK, "Running"),
    "3": (State.CRIT, "Down"),
}


def parse_avaya_88xx(string_table: StringTable) -> Section:
    section = Section(fanstate=[], temp=[])
    for line in string_table:
        section.fanstate.append(line[0])
        section.temp.append(line[1])
    return section


def discover_avaya_88xx(section: Section) -> DiscoveryResult:
    for idx, temp in enumerate(section.temp):
        if temp:
            yield Service(item=str(idx))


def check_avaya_88xx(item: str, params: TempParamType, section: Section) -> CheckResult:
    if len(section.temp) < int(item):
        return
    reading = section.temp[int(item)]
    if reading:
        yield from check_temperature(
            int(reading),
            params,
            unique_name=f"avaya_88xx_{item}",
            value_store=get_value_store(),
        )


def discover_avaya_88xx_fan(section: Section) -> DiscoveryResult:
    for idx, _state in enumerate(section.fanstate):
        yield Service(item=str(idx))


def check_avaya_88xx_fan(item: str, section: Section) -> CheckResult:
    if len(section.fanstate) < int(item):
        return
    if (entry := _FAN_STATE_MAP.get(section.fanstate[int(item)])) is None:
        return
    state, text = entry
    yield Result(state=state, summary=text)


snmp_section_avaya_88xx = SimpleSNMPSection(
    name="avaya_88xx",
    detect=DETECT_AVAYA,
    # RAPID-CITY MIB,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2272.1.4.7.1.1",
        oids=["2", "3"],
    ),
    parse_function=parse_avaya_88xx,
)


check_plugin_avaya_88xx = CheckPlugin(
    name="avaya_88xx",
    service_name="Temperature Fan %s",
    discovery_function=discover_avaya_88xx,
    check_function=check_avaya_88xx,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (55.0, 60.0),
    },
)


check_plugin_avaya_88xx_fan = CheckPlugin(
    name="avaya_88xx_fan",
    service_name="Fan %s Status",
    sections=["avaya_88xx"],
    discovery_function=discover_avaya_88xx_fan,
    check_function=check_avaya_88xx_fan,
)
