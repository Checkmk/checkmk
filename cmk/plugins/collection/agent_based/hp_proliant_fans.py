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
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.hp_proliant import DETECT, sanitize_item, STATUS_MAP

hp_proliant_fans_status_map = {1: "other", 2: "ok", 3: "degraded", 4: "failed"}
hp_proliant_speed_map = {1: "other", 2: "normal", 3: "high"}
hp_proliant_fans_locale = {
    1: "other",
    2: "unknown",
    3: "system",
    4: "systemBoard",
    5: "ioBoard",
    6: "cpu",
    7: "memory",
    8: "storage",
    9: "removableMedia",
    10: "powerSupply",
    11: "ambient",
    12: "chassis",
    13: "bridgeCard",
}

DISCLAIMER = (
    "HPE started to report the speed in percent without updating the MIB.\n"
    "This means that for a reported speed of 'other', 'normal' or 'high', "
    "there is the chance that the speed is actually 1, 2 or 3 percent respectively.\n"
    "This has no influence on the service state."
)


@dataclass(frozen=True)
class Fan:
    index: int
    label: str
    speed: int
    status: int
    is_present: bool
    speed_rpm: int | None

    @classmethod
    def from_line(cls, line: Sequence[str]) -> Self:
        index, _name, present, speed, status, current_speed = line
        return cls(
            index=int(index),
            label=hp_proliant_fans_locale.get(int(line[1]), "other"),
            is_present=present == "3",
            speed=int(speed),
            status=int(status),
            speed_rpm=int(current_speed) if current_speed else None,
        )


Section = Mapping[str, Fan]


def parse_hp_proliant_fans(string_table: StringTable) -> Section:
    return {
        sanitize_item(f"{fan.index} ({fan.label})"): fan
        for line in string_table
        for fan in [Fan.from_line(line)]
    }


snmp_section_hp_proliant_fans = SimpleSNMPSection(
    name="hp_proliant_fans",
    parse_function=parse_hp_proliant_fans,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.232.6.2.6.7.1",
        oids=["2", "3", "4", "6", "9", "12"],
    ),
)


def discover_hp_proliant_fans(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item, fan in section.items() if fan.is_present)


def _make_speed_label(speed: int) -> str:
    try:
        return f"Speed: {hp_proliant_speed_map[speed]}"
    except KeyError:
        # HPE seem to have changed this.
        return f"Speed: {speed}%"


def check_hp_proliant_fans(item: str, section: Section) -> CheckResult:
    if (fan := section.get(item)) is None:
        return

    snmp_status = hp_proliant_fans_status_map[fan.status]
    yield Result(state=STATUS_MAP[snmp_status], summary=f"Status: {snmp_status}")

    speed_label = _make_speed_label(fan.speed)
    yield Result(state=State.OK, summary=speed_label, details=f"{speed_label}\n{DISCLAIMER}")

    if fan.speed_rpm:
        yield from check_levels(fan.speed_rpm, metric_name="rpm", render_func=str, label="RPM")
    return


check_plugin_hp_proliant_fans = CheckPlugin(
    name="hp_proliant_fans",
    service_name="HW FAN%s",
    discovery_function=discover_hp_proliant_fans,
    check_function=check_hp_proliant_fans,
)
