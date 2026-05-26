#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Agent output:
# <<<windows_multipath>>>
# 4
# (yes, thats all)


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


def parse_windows_multipath(string_table: StringTable) -> StringTable:
    return string_table


def discover_windows_multipath(section: StringTable) -> DiscoveryResult:
    try:
        num_active = int(section[0][0])
    except (ValueError, IndexError):
        return

    if num_active > 0:
        yield Service(parameters={"active_paths": num_active})


def check_windows_multipath(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    num_active = int(section[0][0])

    yield Result(state=State.OK, summary=f"Paths active: {num_active}")

    levels = params["active_paths"]
    if isinstance(levels, tuple):
        num_paths, warn, crit = levels
        warn_num = (warn / 100.0) * num_paths
        crit_num = (crit / 100.0) * num_paths
        if num_active < crit_num:
            state = State.CRIT
        elif num_active < warn_num:
            state = State.WARN
        else:
            state = State.OK

        if state is not State.OK:
            yield Result(state=state, summary=f"(warn/crit below {warn_num:.0f}/{crit_num:.0f})")
    else:
        yield Result(state=State.OK, summary=f"Expected paths: {levels}")
        if num_active < levels:
            yield Result(state=State.CRIT, summary=f"(crit below {levels})")
        elif num_active > levels:
            yield Result(state=State.WARN, summary=f"(warn at {levels})")


agent_section_windows_multipath = AgentSection(
    name="windows_multipath",
    parse_function=parse_windows_multipath,
)


check_plugin_windows_multipath = CheckPlugin(
    name="windows_multipath",
    service_name="Multipath",
    discovery_function=discover_windows_multipath,
    check_function=check_windows_multipath,
    check_ruleset_name="windows_multipath",
    check_default_parameters={"active_paths": 4},
)
