#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# <<<hpux_multipath>>>
#       LUN PATH INFORMATION FOR LUN : /dev/rtape/tape1_BEST
# World Wide Identifier(WWID)    = 0x600508b4000139e500049000075e0000
# State                         = UNOPEN
#       LUN PATH INFORMATION FOR LUN : /dev/rdisk/disk10
# World Wide Identifier(WWID)    = 0x600508b4000139e500009000075e00b0
# State                         = ACTIVE
#       LUN PATH INFORMATION FOR LUN : /dev/rdisk/disk13
# World Wide Identifier(WWID)    = 0x600508b4000139e500009000075e00c0
# State                         = UNOPEN
#       LUN PATH INFORMATION FOR LUN : /dev/pt/pt2
# World Wide Identifier(WWID)    = 0x600508b4000139e500009000075e00d0
# State                         = UNOPEN
# State                         = UNOPEN
# State                         = UNOPEN
# State                         = UNOPEN
# State                         = UNOPEN
# State                         = UNOPEN
# State                         = UNOPEN
# State                         = UNOPEN
#         LUN PATH INFORMATION FOR LUN : /dev/rdisk/disk781
# World Wide Identifier(WWID)    = 0x600508b4000139e500009000075e00e0
# State                         = ACTIVE
# State                         = STANDBY
# State                         = FAILED
# State                         = FAILED
# State                         = ACTIVE
# State                         = STANDBY
#       LUN PATH INFORMATION FOR LUN : /dev/rdisk/disk912
# World Wide Identifier(WWID)    = 0x600508b4000139e500009000075e00f0
# State                         = ACTIVE
# State                         = STANDBY
# State                         = ACTIVE
# State                         = STANDBY


from collections.abc import Mapping
from typing import Any

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

hpux_multipath_pathstates = {
    "ACTIVE": 0,
    "STANDBY": 1,
    "FAILED": 2,
    "UNOPEN": 3,
    "OPENING": 0,
    "CLOSING": 1,
}


Section = dict[str, tuple[str, list[int]]]


def parse_hpux_multipath(string_table: StringTable) -> Section:
    disks: Section = {}
    disk = ""
    paths: list[int] = []
    for line in string_table:
        if ":" in line:
            disk = line[-1]
        elif line[0] == "World":
            wwid = line[-1]
            paths = [0, 0, 0, 0]  # ACTIVE, STANBY, FAILED, UNOPEN
            disks[wwid] = (disk, paths)
        elif "=" in line:
            state = line[-1]
            paths[hpux_multipath_pathstates[state]] += 1
    return disks


def discover_hpux_multipath(section: Section) -> DiscoveryResult:
    for wwid, (_disk, (active, standby, failed, unopen)) in section.items():
        if active + standby + failed >= 2:
            yield Service(item=wwid, parameters={"expected": (active, standby, failed, unopen)})


def hpux_multipath_format_pathstatus(pathcounts: list[int] | tuple[int, ...]) -> str:
    infos = []
    for name, i in hpux_multipath_pathstates.items():
        c = pathcounts[i]
        if c > 0:
            infos.append(f"{c} {name}")
    return ", ".join(infos)


def check_hpux_multipath(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    try:
        disk, pathcounts = section[item]
    except KeyError:
        return

    if pathcounts[2] > 0:
        yield Result(
            state=State.CRIT,
            summary=f"{disk}: {pathcounts[2]} failed paths! ({hpux_multipath_format_pathstatus(pathcounts)})",
        )
        return

    expected = params["expected"]
    if list(pathcounts) != list(expected):
        yield Result(
            state=State.WARN,
            summary=(
                f"{disk}: Invalid path status {hpux_multipath_format_pathstatus(pathcounts)} "
                f"(should be {hpux_multipath_format_pathstatus(expected)})"
            ),
        )
    else:
        yield Result(
            state=State.OK,
            summary=f"{disk}: {hpux_multipath_format_pathstatus(pathcounts)}",
        )


agent_section_hpux_multipath = AgentSection(
    name="hpux_multipath",
    parse_function=parse_hpux_multipath,
)


check_plugin_hpux_multipath = CheckPlugin(
    name="hpux_multipath",
    service_name="Multipath %s",
    discovery_function=discover_hpux_multipath,
    check_function=check_hpux_multipath,
    check_ruleset_name="hpux_multipath",
    check_default_parameters={},
)
