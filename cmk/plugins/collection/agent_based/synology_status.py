#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
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
from cmk.plugins.lib import synology


@dataclass(frozen=True)
class Section:
    system: int
    power: int

    @classmethod
    def from_row(cls, row: Sequence[str]) -> "Section":
        return cls(system=int(row[0]), power=int(row[1]))


def parse(string_table: StringTable) -> Section | None:
    """
    assert parse([]) is None
    assert parse([["1","1"]]) == Section(system=1, power=1)
    """
    if not string_table:
        return None
    return Section.from_row(string_table[0])


snmp_section_synology_status = SimpleSNMPSection(
    name="synology_status",
    detect=synology.DETECT,
    parse_function=parse,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.6574.1",
        oids=[
            "1",  # System Status
            "3",  # Power Status
        ],
    ),
)


def discovery(section: Section) -> DiscoveryResult:
    yield Service()


def check(section: Section) -> CheckResult:
    if section.system != 1:
        yield Result(state=State.CRIT, summary="System Failure")
    else:
        yield Result(state=State.OK, summary="System state OK")
    if section.power != 1:
        yield Result(state=State.CRIT, summary="Power Failure")
    else:
        yield Result(state=State.OK, summary="Power state OK")


check_plugin_synology_status = CheckPlugin(
    name="synology_status",
    sections=["synology_status"],
    service_name="Status",
    discovery_function=discovery,
    check_function=check,
)
