#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from dataclasses import dataclass

from cmk.agent_based.v2 import (
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

from .detection import DETECT_BLADE


@dataclass(frozen=True)
class PowerModule:  # can be improved, obviously
    name: str
    present: str
    status: str
    text: str


Section = Mapping[str, PowerModule]


def parse_blade_powermod(string_table: StringTable) -> Section:
    return {line[0]: PowerModule(*line) for line in string_table}


snmp_section_blade_powermod = SimpleSNMPSection(
    name="blade_powermod",
    detect=DETECT_BLADE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2.3.51.2.2.4.1.1",
        oids=["1", "2", "3", "4"],
    ),
    parse_function=parse_blade_powermod,
)


def inventory_blade_powermod(section: Section) -> DiscoveryResult:
    yield from (Service(item=pm.name) for pm in section.values() if pm.present == "1")


def check_blade_powermod(item: str, section: Section) -> CheckResult:
    if (pm := section.get(item)) is None:
        return

    if pm.present != "1":
        yield Result(state=State.CRIT, summary="Not present")
        return

    yield Result(
        state=State.OK if pm.status == "1" else State.CRIT,
        summary=pm.text,
    )


check_plugin_blade_powermod = CheckPlugin(
    name="blade_powermod",
    service_name="Power Module %s",
    discovery_function=inventory_blade_powermod,
    check_function=check_blade_powermod,
)
