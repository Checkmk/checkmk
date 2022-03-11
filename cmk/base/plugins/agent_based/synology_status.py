# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass
from typing import Optional, Sequence

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


@dataclass(frozen=True)
class Section:
    system: int
    power: int

    @classmethod
    def from_row(cls, row: Sequence[str]) -> "Section":
        return cls(system=int(row[0]), power=int(row[1]))


def parse(string_table: StringTable) -> Optional[Section]:
    """
    assert parse([]) is None
    assert parse([["1","1"]]) == Section(system=1, power=1)
    """
    if not string_table:
        return None
    return Section.from_row(string_table[0])


register.snmp_section(
    name="synology_status",
    detect=synology.detect(),
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


register.check_plugin(
    name="synology_status",
    sections=["synology_status"],
    service_name="Status",
    discovery_function=discovery,
    check_function=check,
)
