#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
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

_STATES: Mapping[int, tuple[str, State]] = {
    1: ("OK", State.OK),
    2: ("repairing", State.WARN),
    3: ("migrating", State.WARN),
    4: ("expanding", State.WARN),
    5: ("deleting", State.WARN),
    6: ("creating", State.WARN),
    7: ("RAID syncing", State.OK),
    8: ("RAID parity checking", State.OK),
    9: ("RAID assembling", State.WARN),
    10: ("cancelling", State.WARN),
    11: ("degraded", State.CRIT),
    12: ("crashed", State.CRIT),
    13: ("scrubbing", State.OK),
    14: ("RAID deploying", State.OK),
    15: ("RAID undeploying", State.OK),
    16: ("RAID mounting cache", State.OK),
    17: ("RAID unmounting cache", State.OK),
    18: ("RAID continue expanding", State.WARN),
    19: ("RAID converting", State.OK),
    20: ("RAID migrating", State.OK),
    21: ("RAID status unknown", State.UNKNOWN),
}


@dataclass(frozen=True)
class Raid:
    name: str
    status: int

    @classmethod
    def from_row(cls, row: Sequence[str]) -> "Raid":
        return cls(name=row[0], status=int(row[1]))


Section = Mapping[str, Raid]


def parse(string_table: StringTable) -> Section:
    return {row[0]: Raid.from_row(row) for row in string_table}


snmp_section_synology_raid = SimpleSNMPSection(
    name="synology_raid",
    detect=synology.DETECT,
    parse_function=parse,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.6574.3.1.1",
        oids=[
            "2",  # raidName
            "3",  # raidStatus
        ],
    ),
)


def discovery(section: Section) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check(item: str, section: Section) -> CheckResult:
    raid = section[item]
    summary, state = _STATES[raid.status]
    yield Result(state=state, summary=f"Status: {summary}")


check_plugin_synology_raid = CheckPlugin(
    name="synology_raid",
    sections=["synology_raid"],
    service_name="Raid %s",
    discovery_function=discovery,
    check_function=check,
)
