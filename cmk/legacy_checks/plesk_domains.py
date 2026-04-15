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


def discover_plesk_domains(section: StringTable) -> DiscoveryResult:
    if section and section[0]:
        yield Service()


def check_plesk_domains(section: StringTable) -> CheckResult:
    if not section:
        yield Result(state=State.WARN, summary="No domains configured")
        return
    yield Result(
        state=State.OK,
        summary=section[0][0],
        details="\n".join([i[0] for i in section]),
    )
    return


def parse_plesk_domains(string_table: StringTable) -> StringTable:
    return string_table


agent_section_plesk_domains = AgentSection(
    name="plesk_domains",
    parse_function=parse_plesk_domains,
)


check_plugin_plesk_domains = CheckPlugin(
    name="plesk_domains",
    service_name="Plesk Domains",
    discovery_function=discover_plesk_domains,
    check_function=check_plesk_domains,
)
