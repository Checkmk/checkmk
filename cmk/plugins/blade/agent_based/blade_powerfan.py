#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Self

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)

from .detection import DETECT_BLADE


@dataclass(frozen=True)
class Fan:
    index: str
    present: str
    status: str
    fancount: str
    speedperc: int
    rpm: float
    ctrlstate: str

    @classmethod
    def from_line(cls, line: Sequence[str]) -> Self:
        index, present, status, fancount, speedperc, rpm, ctrlstate = line
        return cls(index, present, status, fancount, int(speedperc), float(rpm), ctrlstate)


Section = Mapping[str, Fan]


def parse_blade_powerfan(string_table: StringTable) -> Section:
    return {fan.index: fan for line in string_table for fan in [Fan.from_line(line)]}


snmp_section_blade_powerfan = SimpleSNMPSection(
    name="blade_powerfan",
    detect=DETECT_BLADE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2.3.51.2.2.6.1.1",
        oids=["1", "2", "3", "4", "5", "6", "7"],
    ),
    parse_function=parse_blade_powerfan,
)


def inventory_blade_powerfan(section: Section) -> DiscoveryResult:
    yield from (Service(item=f.index) for f in section.values() if f.index and f.present == "1")


def check_blade_powerfan(item: str, section: Section) -> CheckResult:
    if (fan := section.get(item)) is None:
        return

    if fan.present != "1":
        yield Result(state=State.CRIT, summary="Fan not present")
        return

    yield from check_levels(
        fan.speedperc,
        metric_name="perc",
        levels_lower=("fixed", (50, 40)),
        label="Speed",
        render_func=render.percent,
        boundaries=(0, 100),
    )
    yield from check_levels(fan.rpm, label="RPM", render_func=str)

    yield Result(
        state=State.OK if fan.status == "1" else State.CRIT,
        notice=f"Status: {'' if fan.status == '1' else 'not '} OK",
    )

    yield Result(
        state=State.OK if fan.ctrlstate == "1" else State.CRIT,
        notice=f"Controller state: {'' if fan.ctrlstate == '1' else 'not '} OK",
    )


check_plugin_blade_powerfan = CheckPlugin(
    name="blade_powerfan",
    service_name="Power Module Cooling Device %s",
    discovery_function=inventory_blade_powerfan,
    check_function=check_blade_powerfan,
)
