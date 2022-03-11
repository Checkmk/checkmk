# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass
from typing import Mapping, Sequence, Tuple

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    register,
    Result,
    Service,
    SNMPTree,
    State,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)
from cmk.base.plugins.agent_based.utils import synology

_STATES: Mapping[int, Tuple[str, State]] = {
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


register.snmp_section(
    name="synology_raid",
    detect=synology.detect(),
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


register.check_plugin(
    name="synology_raid",
    sections=["synology_raid"],
    service_name="Raid %s",
    discovery_function=discovery,
    check_function=check,
)
