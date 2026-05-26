#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


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


def parse_tsm_paths(string_table: StringTable) -> StringTable:
    return string_table


def discover_tsm_paths(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


def check_tsm_paths(section: StringTable) -> CheckResult:
    error_paths = [line[1] for line in section if line[2] != "YES"]
    if error_paths:
        yield Result(
            state=State.CRIT,
            summary=f"Paths with errors: {', '.join(error_paths)}",
        )
        return
    yield Result(state=State.OK, summary=f"{len(section)} paths OK")


agent_section_tsm_paths = AgentSection(
    name="tsm_paths",
    parse_function=parse_tsm_paths,
)


check_plugin_tsm_paths = CheckPlugin(
    name="tsm_paths",
    service_name="TSM Paths",
    discovery_function=discover_tsm_paths,
    check_function=check_tsm_paths,
)
