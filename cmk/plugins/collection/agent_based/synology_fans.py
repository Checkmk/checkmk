#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
from collections.abc import Mapping

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


class FanStatus(enum.Enum):
    NORMAL = 1
    FAILURE = 2


Section = Mapping[str, FanStatus]


def parse(string_table: StringTable) -> Section | None:
    """
    >>> assert parse([]) is None
    >>> assert parse([["1","2"]]) == {"System": FanStatus.NORMAL, "CPU": FanStatus.FAILURE}
    """
    if not string_table:
        return None
    row = string_table[0]
    return {
        "System": FanStatus(int(row[0])),
        "CPU": FanStatus(int(row[1])),
    }


snmp_section_synology_fans = SimpleSNMPSection(
    name="synology_fans",
    detect=synology.DETECT,
    parse_function=parse,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.6574.1.4",
        oids=[
            "1",  # System fan
            "2",  # CPU fan
        ],
    ),
)


def discovery(section: Section) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check(item: str, section: Section) -> CheckResult:
    if not (fan_status := section.get(item)):
        return
    yield (
        Result(
            state=State.OK,
            summary="Operating normally",
        )
        if fan_status is FanStatus.NORMAL
        else Result(
            state=State.CRIT,
            summary="Fan failed",
        )
    )


check_plugin_synology_fans = CheckPlugin(
    name="synology_fans",
    service_name="Fan %s",
    discovery_function=discovery,
    check_function=check,
)
