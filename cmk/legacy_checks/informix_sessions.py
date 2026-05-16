#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    StringTable,
)

Section = Mapping[str, str]


def parse_informix_sessions(string_table: StringTable) -> Section:
    parsed: dict[str, str] = {}
    instance: str | None = None
    for line in string_table:
        if line[0].startswith("[[[") and line[0].endswith("]]]"):
            instance = line[0][3:-3]

        elif instance is not None and line[0] == "SESSIONS":
            parsed.setdefault(instance, line[1])

    return parsed


def discover_informix_sessions(section: Section) -> DiscoveryResult:
    for instance in section:
        yield Service(item=instance)


def check_informix_sessions(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if item not in section:
        return
    sessions = int(section[item])
    warn, crit = params["levels"]

    yield from check_levels_v1(
        sessions,
        metric_name="sessions",
        levels_upper=(warn, crit),
        label="Sessions",
    )


agent_section_informix_sessions = AgentSection(
    name="informix_sessions",
    parse_function=parse_informix_sessions,
)


check_plugin_informix_sessions = CheckPlugin(
    name="informix_sessions",
    service_name="Informix Sessions %s",
    discovery_function=discover_informix_sessions,
    check_function=check_informix_sessions,
    check_ruleset_name="informix_sessions",
    check_default_parameters={"levels": (50, 60)},
)
