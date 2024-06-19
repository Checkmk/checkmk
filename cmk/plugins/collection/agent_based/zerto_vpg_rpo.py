#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# 2019-01-07, comNET GmbH, Fabian Binder

from collections.abc import Mapping
from typing import TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)

MAP_RPO_STATES = {
    "0": (State.WARN, "VPG is initializing"),
    "1": (State.OK, "Meeting SLA specification"),
    "2": (State.CRIT, "Not meeting SLA specification for RPO SLA and journal history"),
    "3": (State.CRIT, "Not meeting SLA specification for RPO SLA"),
    "4": (State.CRIT, "Not meeting SLA specification for journal history"),
    "5": (State.WARN, "VPG is in a failover operation"),
    "6": (State.WARN, "VPG is in a move operation"),
    "7": (State.WARN, "VPG is being deleted"),
    "8": (State.WARN, "VPG has been recovered"),
}


class VPG(TypedDict):
    state: str
    actual_rpo: str


Section = Mapping[str, VPG]


def parse_zerto_vpg(string_table: StringTable) -> Section:
    parsed: dict[str, VPG] = {}
    for line in string_table:
        if len(line) < 3:
            continue
        vpgname = line[0]
        parsed.setdefault(vpgname, VPG(state=line[1], actual_rpo=line[2]))
    return parsed


def check_zerto_vpg_rpo(item: str, section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return
    state, vpg_info = MAP_RPO_STATES.get(data.get("state", ""), (State.UNKNOWN, "Unknown"))
    yield Result(state=state, summary="VPG Status: %s" % vpg_info)


def discover_zerto_vpg_rpo(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


agent_section_zerto_vpg_rpo = AgentSection(name="zerto_vpg_rpo", parse_function=parse_zerto_vpg)
check_plugin_zerto_vpg_rpo = CheckPlugin(
    name="zerto_vpg_rpo",
    service_name="Zerto VPG RPO %s",
    discovery_function=discover_zerto_vpg_rpo,
    check_function=check_zerto_vpg_rpo,
)
