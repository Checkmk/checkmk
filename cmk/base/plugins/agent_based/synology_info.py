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
    model: str
    serialnumber: str
    os: str

    @classmethod
    def from_row(cls, row: Sequence[str]) -> "Section":
        return cls(model=row[0], serialnumber=row[1], os=row[2])


def parse(string_table: StringTable) -> Optional[Section]:
    """
    >>> assert parse([]) is None
    >>> assert parse([["model", "SN7", "DSM"]]) == Section(model="model", serialnumber="SN7", os="DSM")
    """
    if not string_table:
        return None
    return Section.from_row(string_table[0])


register.snmp_section(
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


register.check_plugin(
    name="synology_info",
    sections=["synology_info"],
    service_name="Info",
    discovery_function=discovery,
    check_function=check,
)
