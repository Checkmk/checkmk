#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:


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


def discover_symantec_av_progstate(section: StringTable) -> DiscoveryResult:  # noqa: ARG001
    yield Service()


def check_symantec_av_progstate(section: StringTable) -> CheckResult:
    if section[0][0].lower() != "enabled":
        yield Result(state=State.CRIT, summary=f"Program Status is {section[0][0]}")
        return
    yield Result(state=State.OK, summary="Program enabled")


def parse_symantec_av_progstate(string_table: StringTable) -> StringTable:
    return string_table


agent_section_symantec_av_progstate = AgentSection(
    name="symantec_av_progstate",
    parse_function=parse_symantec_av_progstate,
)

check_plugin_symantec_av_progstate = CheckPlugin(
    name="symantec_av_progstate",
    service_name="AV Program Status",
    discovery_function=discover_symantec_av_progstate,
    check_function=check_symantec_av_progstate,
)
