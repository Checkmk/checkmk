#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="unreachable"

# <<<oracle_sessions>>>
# pengt  15
# hirni  22
# newdb  47 772 65


# mypy: disable-error-code="var-annotated"

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    render,
    Result,
    Service,
    State,
    StringTable,
)

# Type alias for the section data structure
# Maps instance name -> session metrics (cursess, maxsess, curmax)
type SectionOracleSessions = Mapping[str, Mapping[str, int]]


def parse_oracle_sessions(string_table: StringTable) -> SectionOracleSessions:
    header = ["cursess", "maxsess", "curmax"]
    parsed = {}
    for line in string_table:
        for key, entry in zip(header, line[1:]):
            try:
                parsed.setdefault(line[0], {})[key] = int(entry)
            except ValueError:
                pass
    return parsed


def discover_oracle_sessions(section: SectionOracleSessions) -> DiscoveryResult:
    for sid in section:
        yield Service(item=sid)


def check_oracle_sessions(
    item: str, params: Mapping[str, Any], section: SectionOracleSessions
) -> CheckResult:
    if isinstance(params, tuple):
        params = {"sessions_abs": params}

    if (data := section.get(item)) is None or "cursess" not in data:
        # In case of missing information we assume that the login into
        # the database has failed and we simply skip this check. It won't
        # switch to UNKNOWN, but will get stale.
        raise IgnoreResultsError("Login into database failed")

    sessions = data["cursess"]
    sessions_max = data.get("maxsess")

    yield from check_levels(
        sessions,
        metric_name="sessions",
        levels_upper=("fixed", levels)
        if (levels := params["sessions_abs"]) is not None
        else ("no_levels", None),
        render_func=str,
        label="Sessions",
        boundaries=(0, sessions_max),
    )

    if sessions_max is not None:
        sessions_perc = 100.0 * sessions / sessions_max
        yield from check_levels(
            sessions_perc,
            levels_upper=("fixed", params["sessions_perc"])
            if "sessions_perc" in params
            else ("no_levels", None),
            render_func=render.percent,
            label=f"Sessions ({sessions} of {sessions_max})",
        )
        yield Result(state=State.OK, summary=f"Maximum: {sessions_max}")


agent_section_oracle_sessions = AgentSection(
    name="oracle_sessions",
    parse_function=parse_oracle_sessions,
)


check_plugin_oracle_sessions = CheckPlugin(
    name="oracle_sessions",
    service_name="ORA %s Sessions",
    discovery_function=discover_oracle_sessions,
    check_function=check_oracle_sessions,
    check_ruleset_name="oracle_sessions",
    check_default_parameters={
        "sessions_abs": (150, 300),
    },
)
