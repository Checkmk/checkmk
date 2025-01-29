#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final, Literal

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
from cmk.plugins.lib.threepar import parse_3par

THREEPAR_REMOTECOPY_DEFAULT_LEVELS: Final[Mapping[str, Literal[0, 1, 2, 3]]] = {
    "1": 0,  # NORMAL
    "2": 1,  # STARTUP
    "3": 1,  # SHUTDOWN
    "4": 0,  # ENABLE
    "5": 2,  # DISABLE
    "6": 2,  # INVALID
    "7": 1,  # NODEDUP
    "8": 0,  # UPGRADE
}

MODES = {
    1: Result(state=State.UNKNOWN, summary="Mode: NONE"),
    2: Result(state=State.OK, summary="Mode: STARTED"),
    3: Result(state=State.CRIT, summary="Mode: STOPPED"),
}

STATUSES = {
    1: "NORMAL",
    2: "STARTUP",
    3: "SHUTDOWN",
    4: "ENABLE",
    5: "DISABLE",
    6: "INVALID",
    7: "NODEDUP",
    8: "UPGRADE",
}


@dataclass
class ThreeparRemoteCopy:
    mode: int
    status: str
    status_readable: str


def parse_threepar_remotecopy(string_table: StringTable) -> ThreeparRemoteCopy:
    pre_parsed = parse_3par(string_table)

    return ThreeparRemoteCopy(
        mode=pre_parsed.get("mode", 1),
        status=str(pre_parsed.get("status", 6)),
        status_readable=STATUSES[pre_parsed.get("status", 6)],
    )


agent_section_3par_remotecopy = AgentSection(
    name="3par_remotecopy",
    parse_function=parse_threepar_remotecopy,
)


def discover_threepar_remotecopy(section: ThreeparRemoteCopy) -> DiscoveryResult:
    if section.mode > 1:
        yield Service()


def check_threepar_remotecopy(
    params: Mapping[str, Literal[0, 1, 2, 3]],
    section: ThreeparRemoteCopy,
) -> CheckResult:
    yield MODES[section.mode]

    yield Result(
        state=State(params[section.status]),
        summary=f"Status: {section.status_readable}",
    )


check_plugin_3par_remotecopy = CheckPlugin(
    name="3par_remotecopy",
    service_name="Remote copy",
    discovery_function=discover_threepar_remotecopy,
    check_function=check_threepar_remotecopy,
    check_default_parameters=THREEPAR_REMOTECOPY_DEFAULT_LEVELS,
    check_ruleset_name="threepar_remotecopy",
)
