#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<citrix_sessions>>>
# sessions 1
# active_sessions 1
# inactive_sessions 0


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
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


def parse_citrix_sessions(string_table: StringTable) -> StringTable:
    return string_table


def discover_citrix_sessions(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_citrix_sessions(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    session: dict[str, int] = {}
    for line in section:
        if len(line) > 1:
            session.setdefault(line[0], int(line[1]))

    if not session:
        yield Result(
            state=State.UNKNOWN,
            summary="Could not collect session information. Please check the agent configuration.",
        )
        return

    for key, what in [
        ("sessions", "total"),
        ("active_sessions", "active"),
        ("inactive_sessions", "inactive"),
    ]:
        if session.get(key) is None:
            continue
        yield from check_levels_v1(
            session[key],
            metric_name=what,
            levels_upper=params.get(what),
            label=what.title(),
        )


agent_section_citrix_sessions = AgentSection(
    name="citrix_sessions",
    parse_function=parse_citrix_sessions,
)


check_plugin_citrix_sessions = CheckPlugin(
    name="citrix_sessions",
    service_name="Citrix Sessions",
    discovery_function=discover_citrix_sessions,
    check_function=check_citrix_sessions,
    check_ruleset_name="citrix_sessions",
    check_default_parameters={
        "total": (60, 65),
        "active": (60, 65),
        "inactive": (10, 15),
    },
)
