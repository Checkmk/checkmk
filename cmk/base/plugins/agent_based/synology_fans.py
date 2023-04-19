#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
from collections.abc import Mapping

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


register.snmp_section(
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
    yield Result(
        state=State.OK,
        summary="Operating normally",
    ) if fan_status is FanStatus.NORMAL else Result(
        state=State.CRIT,
        summary="Fan failed",
    )


register.check_plugin(
    name="synology_fans",
    service_name="Fan %s",
    discovery_function=discovery,
    check_function=check,
)
