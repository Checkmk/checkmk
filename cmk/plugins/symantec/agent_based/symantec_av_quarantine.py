#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# List of Objects, else Empty


from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)


def discover_symantec_av_quarantine(section: StringTable) -> DiscoveryResult:  # noqa: ARG001
    yield Service()


def check_symantec_av_quarantine(section: StringTable) -> CheckResult:
    if len(section) > 0:
        yield Result(state=State.CRIT, summary=f"{len(section)} objects in quarantine")
    else:
        yield Result(state=State.OK, summary="No objects in quarantine")
    yield Metric("objects", len(section))


def parse_symantec_av_quarantine(string_table: StringTable) -> StringTable:
    return string_table


agent_section_symantec_av_quarantine = AgentSection(
    name="symantec_av_quarantine",
    parse_function=parse_symantec_av_quarantine,
)

check_plugin_symantec_av_quarantine = CheckPlugin(
    name="symantec_av_quarantine",
    service_name="AV Quarantine",
    discovery_function=discover_symantec_av_quarantine,
    check_function=check_symantec_av_quarantine,
)
