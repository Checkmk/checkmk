#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# <<<hyperv_vmstatus>>>
# Integration_Services Ok
# Replica_Health None


from collections.abc import Mapping

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

Section = Mapping[str, str]


def parse_hyperv_vmstatus(string_table: StringTable) -> Section:
    return {line[0]: " ".join(line[1:]) for line in string_table}


def discover_hyperv_vmstatus(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_hyperv_vmstatus(section: Section) -> CheckResult:
    int_state = section.get("Integration_Services")
    # According to microsoft 'Protocol_Mismatch' is OK:
    #   The secondary status [...] includes an error string that sounds alarming
    #   but that you can safely ignore. [...] This behavior is by design.
    state = State.OK if int_state in ("Ok", "Protocol_Mismatch") else State.CRIT
    yield Result(state=state, summary=f"Integration Service State: {int_state}")


agent_section_hyperv_vmstatus = AgentSection(
    name="hyperv_vmstatus",
    parse_function=parse_hyperv_vmstatus,
)


check_plugin_hyperv_vmstatus = CheckPlugin(
    name="hyperv_vmstatus",
    service_name="HyperV Status",
    discovery_function=discover_hyperv_vmstatus,
    check_function=check_hyperv_vmstatus,
)
