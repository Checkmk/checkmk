#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from enum import Enum
from typing import NamedTuple, Self

from cmk.agent_based.v2 import (
    all_of,
    DiscoveryResult,
    exists,
    OIDEnd,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.agent_based.v3_unstable import CheckPlugin, CheckResult, parse_as, ParseFailure
from cmk.plugins.aruba.lib import DETECT_2930M


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
    tray: int | None | ParseFailure
    type: FanType | ParseFailure
    state: FanState | ParseFailure
    failures: int | None | ParseFailure

    @classmethod
    def parse(cls, entry: Sequence[str]) -> Self:
        _key, tray, fan_type, state, failures = entry
        return cls(
            tray=cls._parse_count(tray, field="hpicfFanTray"),
            type=parse_as(FanType, fan_type, field="hpicfFanType"),
            state=parse_as(FanState, state, field="hpicfFanState"),
            failures=cls._parse_count(failures, field="hpicfFanNumFailures"),
        )

    @staticmethod
    def _parse_count(raw: str, *, field: str) -> int | None | ParseFailure:
        return None if raw == "" else parse_as(int, raw, field=field)


Section = Mapping[str, Fan]

TemperatureParams = tuple[float, float]


def parse_aruba_fans(string_table: StringTable) -> Section:
    return {f"{int(entry[0]):06d}": Fan.parse(entry) for entry in string_table}


snmp_section_aruba_fan_status = SimpleSNMPSection(
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
    for item in section:
        yield Service(item=item)


def check_aruba_fan_status(
    item: str,
    section: Section,
) -> CheckResult:
    if (fan := section.get(item)) is None:
        return

    if isinstance(fan.state, ParseFailure):
        yield fan.state
    else:
        yield Result(
            state=FanStateMapping[fan.state],
            summary=f"Fan Status: {fan.state.name}",
        )

    if isinstance(fan.type, ParseFailure):
        yield fan.type
    else:
        yield Result(state=State.OK, summary=f"Type: {fan.type.name}")

    if isinstance(fan.tray, ParseFailure):
        yield fan.tray
    elif fan.tray is not None:
        yield Result(state=State.OK, summary=f"Tray: {fan.tray}")

    if isinstance(fan.failures, ParseFailure):
        yield fan.failures
    elif fan.failures is not None and fan.failures > 0:
        yield Result(state=State.OK, summary=f"Failures: {fan.failures}")


check_plugin_aruba_fan_status = CheckPlugin(
    name="aruba_fan_status",
    service_name="Fan Status %s",
    discovery_function=discover_aruba_fan_status,
    check_function=check_aruba_fan_status,
)
