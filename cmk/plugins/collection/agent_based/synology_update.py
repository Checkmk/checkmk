#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

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
from cmk.plugins.lib import synology

_STATES: Mapping[int, str] = {
    1: "Available",
    2: "Unavailable",
    3: "Connecting",
    4: "Disconnected",
    5: "Others",
}


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


def check(params: Mapping[str, Any], section: Section) -> CheckResult:
    state = State.UNKNOWN
    if section.status in params["ok_states"]:
        state = State.OK
    elif section.status in params["warn_states"]:
        state = State.WARN
    elif section.status in params["crit_states"]:
        state = State.CRIT
    elif section.status == 3:
        # to prevent flapping between update avail and Connection
        raise IgnoreResultsError("Devices try to connect to the update server")
    yield Result(
        state=state,
        summary=f"Update Status: {_STATES[section.status]}, Current Version: {section.version}",
    )


check_plugin_synology_update = CheckPlugin(
    name="synology_update",
    sections=["synology_update"],
    service_name="Update",
    discovery_function=discovery,
    check_function=check,
    check_ruleset_name="synology_update",
    check_default_parameters={
        "ok_states": [2],
        "warn_states": [5],
        "crit_states": [1, 4],
    },
)
