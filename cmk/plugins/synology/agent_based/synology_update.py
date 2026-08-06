#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from typing import TypedDict

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.synology import lib as synology


class Status(Enum):
    AVAILABLE = 1
    UNAVAILABLE = 2
    CONNECTING = 3
    DISCONNECTED = 4
    OTHERS = 5

    @property
    def ruleset_name(self) -> str:
        return self.name.lower()

    @property
    def title(self) -> str:
        return self.name.capitalize()


class Params(TypedDict):
    ok_states: Sequence[str]
    warn_states: Sequence[str]
    crit_states: Sequence[str]


@dataclass(frozen=True)
class Section:
    version: str
    status: int

    @classmethod
    def from_row(cls, row: Sequence[str]) -> "Section":
        return cls(version=row[0], status=int(row[1]))


def parse(string_table: StringTable) -> Section | None:
    """
    assert parse([]) is None
    assert parse([["DSM 7", "0"]]) == Section(version="DSM 7", status=0)
    """
    if not string_table:
        return None
    return Section.from_row(string_table[0])


snmp_section_synology_update = SimpleSNMPSection(
    name="synology_update",
    detect=synology.DETECT,
    parse_function=parse,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.6574.1.5",
        oids=[
            "3",  # Version
            "4",  # Status
        ],
    ),
)


def discovery(section: Section) -> DiscoveryResult:
    yield Service()


def check(params: Params, section: Section) -> CheckResult:
    status = Status(section.status)
    state = State.UNKNOWN
    if status.ruleset_name in params["ok_states"]:
        state = State.OK
    elif status.ruleset_name in params["warn_states"]:
        state = State.WARN
    elif status.ruleset_name in params["crit_states"]:
        state = State.CRIT
    elif status is Status.CONNECTING:
        # to prevent flapping between update avail and Connection
        raise IgnoreResultsError("Devices try to connect to the update server")
    yield Result(
        state=state,
        summary=f"Update Status: {status.title}, Current Version: {section.version}",
    )


check_plugin_synology_update = CheckPlugin(
    name="synology_update",
    sections=["synology_update"],
    service_name="Update",
    discovery_function=discovery,
    check_function=check,
    check_ruleset_name="synology_update",
    check_default_parameters=Params(
        ok_states=[Status.UNAVAILABLE.ruleset_name],
        warn_states=[Status.OTHERS.ruleset_name],
        crit_states=[Status.AVAILABLE.ruleset_name, Status.DISCONNECTED.ruleset_name],
    ),
)
