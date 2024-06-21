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
    model: str
    serialnumber: str
    os: str

    @classmethod
    def from_row(cls, row: Sequence[str]) -> "Section":
        return cls(model=row[0], serialnumber=row[1], os=row[2])


def parse(string_table: StringTable) -> Section | None:
    """
    >>> assert parse([]) is None
    >>> assert parse([["model", "SN7", "DSM"]]) == Section(model="model", serialnumber="SN7", os="DSM")
    """
    if not string_table:
        return None
    return Section.from_row(string_table[0])


snmp_section_synology_info = SimpleSNMPSection(
    name="synology_info",
    detect=synology.DETECT,
    parse_function=parse,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.6574.1.5",
        oids=[
            "1",  # Model
            "2",  # SerialNumber
            "3",  # OS Version
        ],
    ),
)


def discovery(section: Section) -> DiscoveryResult:
    yield Service()


def check(section: Section) -> CheckResult:
    summary = f"Model: {section.model}, S/N: {section.serialnumber}, OS Version: {section.os}"
    yield Result(state=State.OK, summary=summary)


check_plugin_synology_info = CheckPlugin(
    name="synology_info",
    sections=["synology_info"],
    service_name="Info",
    discovery_function=discovery,
    check_function=check,
)
