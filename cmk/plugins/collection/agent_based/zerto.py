#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass

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


@dataclass
class Section:
    has_errors: bool
    error_details: str | None = None


def parse(string_table: StringTable) -> Section:
    for line in string_table:
        if "Error" in line[0]:
            return Section(True, error_details=" ".join(line[0].split(":")[1:]).strip())

    return Section(False)


agent_section_zerto_agent = AgentSection(name="zerto_agent", parse_function=parse)


def discovery(section: Section) -> DiscoveryResult:
    yield Service()


def check(section: Section) -> CheckResult:
    if section.has_errors:
        yield Result(
            state=State.CRIT,
            summary="Error starting agent",
            details=section.error_details,
        )
    else:
        yield Result(state=State.OK, summary="Agent started without problem")


check_plugin_zerto_agent = CheckPlugin(
    name="zerto_agent",
    service_name="Zerto Agent Status",
    discovery_function=discovery,
    check_function=check,
)
