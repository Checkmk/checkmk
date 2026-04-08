#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import TypedDict

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    OIDEnd,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.elphase import check_elphase, ElPhase

from .detection import DETECT_BLADE


class BayData(TypedDict):
    type: str
    id: str
    power_max: int
    device_state: tuple[int, str]
    power: int


Section = Mapping[str, BayData]

_MAP_STATES: Mapping[str, tuple[int, str]] = {
    "0": (0, "standby"),
    "1": (0, "on"),
    "2": (1, "not present"),
    "3": (1, "switched off"),
    "255": (2, "not applicable"),
}


def parse_blade_bays(string_table: Sequence[StringTable]) -> Section:
    parsed: dict[str, BayData] = {}
    for power_domain, block in enumerate(string_table):
        for oid, name, state, ty, identifier, power_str, power_max_str in block:
            if (itemname := f"PD{power_domain + 1} {name}") in parsed:
                itemname = f"{itemname} {oid}"

            try:
                power = int(power_str.rstrip("W"))
                power_max = int(power_max_str.rstrip("W"))
            except ValueError:
                power = 0
                power_max = 0

            parsed.setdefault(
                itemname,
                BayData(
                    type=ty.split("(")[0],
                    id=identifier,
                    power_max=power_max,
                    device_state=_MAP_STATES.get(state, (3, f"unhandled[{state}]")),
                    power=power,
                ),
            )

    return parsed


def discover_blade_bays(section: Section) -> DiscoveryResult:
    for entry, attrs in section.items():
        if attrs["device_state"][1] in ["standby", "on"]:
            yield Service(item=entry)


def check_blade_bays(item: str, section: Section) -> CheckResult:
    if (data := section.get(item)) is None:
        yield Result(state=State.UNKNOWN, summary=f"No data for '{item}' in SNMP info")
        return

    state_int, state_readable = data["device_state"]
    yield Result(state=State(state_int), summary=f"Status: {state_readable}")
    yield from check_elphase(params={}, elphase=ElPhase.from_dict(data))
    yield Result(state=State.OK, summary=f"Max. power: {data['power_max']} W")
    yield Result(state=State.OK, summary=f"ID: {data['id']}")


snmp_section_blade_bays = SNMPSection(
    name="blade_bays",
    detect=DETECT_BLADE,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.2.3.51.2.2.10.2.1.1",
            oids=[OIDEnd(), "5", "6", "2", "1", "7", "8"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.2.3.51.2.2.10.3.1.1",
            oids=[OIDEnd(), "5", "6", "2", "1", "7", "8"],
        ),
    ],
    parse_function=parse_blade_bays,
)


check_plugin_blade_bays = CheckPlugin(
    name="blade_bays",
    service_name="BAY %s",
    discovery_function=discover_blade_bays,
    check_function=check_blade_bays,
)
