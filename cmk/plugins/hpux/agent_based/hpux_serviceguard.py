#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<hpux_serviceguard:sep(124)>>>
# summary=degraded
# node:hgs-sd1-srv2|summary=ok
# node:hgs-sd1-srv1|summary=ok
# node:hgs-sd2-srv1|summary=ok
# package:AKKP|summary=degraded
# package:ADBP|summary=degraded
# package:ADBT|summary=degraded
# package:KORRP|summary=degraded
# package:KVNAP|summary=degraded
# package:ARCP|summary=degraded
# package:AKKT|summary=degraded
# package:AVDT|summary=degraded
# package:KVNAB|summary=degraded
# package:AVDP|summary=degraded
# package:SDBP|summary=degraded


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


def discover_hpux_serviceguard(section: StringTable) -> DiscoveryResult:
    for line in section:
        if len(line) == 1:
            yield Service(item="Total Status")
        else:
            yield Service(item=line[0])


def check_hpux_serviceguard(item: str, section: StringTable) -> CheckResult:
    for line in section:
        if (item == "Total Status" and len(line) == 1) or (item == line[0] and len(line) == 2):
            status = line[-1].split("=")[-1]
            if status == "ok":
                state = State.OK
            elif status == "degraded":
                state = State.WARN
            else:
                state = State.CRIT
            yield Result(state=state, summary=f"state is {status}")
            return

    yield Result(state=State.UNKNOWN, summary="No such item found")


def parse_hpux_serviceguard(string_table: StringTable) -> StringTable:
    return string_table


agent_section_hpux_serviceguard = AgentSection(
    name="hpux_serviceguard",
    parse_function=parse_hpux_serviceguard,
)


check_plugin_hpux_serviceguard = CheckPlugin(
    name="hpux_serviceguard",
    service_name="Serviceguard %s",
    discovery_function=discover_hpux_serviceguard,
    check_function=check_hpux_serviceguard,
)
