# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Mapping, Optional

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

Section = Mapping[str, int]


def parse(string_table: StringTable) -> Optional[Section]:
    """
    >>> assert parse([]) is None
    >>> assert parse([["0","1"]]) == {"System": 0, "CPU": 1}
    """
    if not string_table:
        return None
    row = string_table[0]
    return {"System": int(row[0]), "CPU": int(row[1])}


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
    if section[item] != 1:
        state, summary = (State.OK, "No failure reported")
    else:
        state, summary = (State.CRIT, "Section Failed")
    yield Result(state=state, summary=summary)


register.check_plugin(
    name="synology_fans",
    sections=["synology_fans"],
    service_name="Section %s",
    discovery_function=discovery,
    check_function=check,
)
