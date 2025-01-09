#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# <<<winperf_ts_sessions>>>
# 1385714515.93 2102
# 2 20 rawcount
# 4 18 rawcount
# 6 2 rawcount

# Counters, relative to the base ID (e.g. 2102)
# 2 Total number of Terminal Services sessions.
# 4 Number of active Terminal Services sessions.
# 6 Number of inactive Terminal Services sessions.
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)


def discovery_winperf_ts_sessions(
    section: StringTable,
) -> DiscoveryResult:
    if len(section) > 1:
        yield Service()


def check_winperf_ts_sessions(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    if not section or len(section) == 1:
        yield Result(state=State.UNKNOWN, summary="Performance counters not available")
    total, active, inactive = (int(l[1]) for l in section[1:4])

    # Tom Moore said, that the order of the columns has recently changed
    # in newer Windows versions (hooray!) and is now active, inactive, total.
    # We try to accommodate for that.
    if active + inactive != total:
        active, inactive, total = total, active, inactive

    limit_active = params.get("active", None)
    limit_inactive = params.get("inactive", None)

    yield from check_levels(
        value=active,
        metric_name="active",
        levels_upper=("fixed", limit_active) if limit_active else ("no_levels", limit_active),
        render_func=lambda x: f"{x} Active",
    )
    yield from check_levels(
        value=inactive,
        metric_name="inactive",
        levels_upper=("fixed", limit_inactive) if limit_inactive else ("no_levels", limit_inactive),
        render_func=lambda x: f"{x} Inactive",
    )


def parse_winperf_ts_sessions(string_table: StringTable) -> StringTable:
    return string_table


agent_section_winperf_ts_sessions = AgentSection(
    name="winperf_ts_sessions", parse_function=parse_winperf_ts_sessions
)
check_plugin_winperf_ts_sessions = CheckPlugin(
    name="winperf_ts_sessions",
    service_name="Sessions",
    discovery_function=discovery_winperf_ts_sessions,
    check_function=check_winperf_ts_sessions,
    check_ruleset_name="winperf_ts_sessions",
    check_default_parameters={},
)
