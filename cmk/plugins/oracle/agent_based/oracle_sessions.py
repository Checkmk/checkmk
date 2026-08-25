#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"
# mypy: disable-error-code="unreachable"

# <<<oracle_sessions>>>
# pengt  15
# hirni  22
# newdb  47 772 65


import contextlib
from collections.abc import Mapping
from dataclasses import dataclass, field
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

from .liboracle import oracle_handle_ora_errors


@dataclass
class OracleSession:
    metrics: dict[str, int] = field(default_factory=dict)
    error: str | None = None


type SectionOracleSessions = Mapping[str, OracleSession]


def parse_oracle_sessions(string_table: StringTable) -> SectionOracleSessions:
    header = ["cursess", "maxsess", "curmax"]
    parsed: dict[str, OracleSession] = {}
    for line in string_table:
        if len(line) == 3 and line[1] == "FAILURE":
            error = oracle_handle_ora_errors(line)
            if isinstance(error, Result):
                parsed.setdefault(line[0], OracleSession()).error = error.summary
            continue
        for key, entry in zip(header, line[1:]):
            with contextlib.suppress(ValueError):
                parsed.setdefault(line[0], OracleSession()).metrics[key] = int(entry)
    return parsed


def discover_oracle_sessions(section: SectionOracleSessions) -> DiscoveryResult:
    for sid, data in section.items():
        if data.metrics:
            yield Service(item=sid)


def check_oracle_sessions(
    item: str, params: Mapping[str, Any], section: SectionOracleSessions
) -> CheckResult:
    if isinstance(params, tuple):
        params = {"sessions_abs": params}

    data = section.get(item)
    if data is None:
        # In case of missing information we assume that the login into
        # the database has failed and we simply skip this check. It won't
        # switch to UNKNOWN, but will get stale.
        raise IgnoreResultsError("Login into database failed")

    if data.error is not None:
        yield Result(state=State.UNKNOWN, summary=data.error)
        return

    if "cursess" not in data.metrics:
        raise IgnoreResultsError("Login into database failed")

    sessions = data.metrics["cursess"]
    sessions_max = data.metrics.get("maxsess")

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
