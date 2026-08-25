#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

# <<<oracle_sessions>>>
# pengt  15
# hirni  22
# newdb  47 772 65


import contextlib
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

from .liboracle import Error, Ok, oracle_handle_ora_errors, Parsed

type _Metrics = dict[str, int]
type Section = Mapping[str, Parsed[_Metrics]]


def parse_oracle_sessions(string_table: StringTable) -> Section:
    header = ["cursess", "maxsess", "curmax"]
    metrics_by_sid: dict[str, _Metrics] = {}
    errors: dict[str, str] = {}
    for line in string_table:
        match oracle_handle_ora_errors(line):
            case str() as message:
                errors.setdefault(line[0], message)
            case False:
                continue
            case None:
                for key, entry in zip(header, line[1:]):
                    with contextlib.suppress(ValueError):
                        metrics_by_sid.setdefault(line[0], {})[key] = int(entry)

    parsed: dict[str, Parsed[_Metrics]] = {
        sid: Ok(metrics) for sid, metrics in metrics_by_sid.items() if sid not in errors
    }
    for sid, message in errors.items():
        parsed[sid] = Error(message)
    return parsed


def discover_oracle_sessions(section: Section) -> DiscoveryResult:
    for sid, result in section.items():
        if isinstance(result, Ok) and result.value:
            yield Service(item=sid)


def check_oracle_sessions(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if isinstance(params, tuple):  # type: ignore[unreachable]
        params = {"sessions_abs": params}  # type: ignore[unreachable]

    match section.get(item):
        case None:
            # In case of missing information we assume that the login into
            # the database has failed and we simply skip this check. It won't
            # switch to UNKNOWN, but will get stale.
            raise IgnoreResultsError("Login into database failed")
        case Error(message):
            yield Result(state=State.UNKNOWN, summary=message)
        case Ok(metrics):
            yield from _check_sessions(params, metrics)


def _check_sessions(params: Mapping[str, Any], metrics: _Metrics) -> CheckResult:
    if "cursess" not in metrics:
        raise IgnoreResultsError("Login into database failed")

    sessions = metrics["cursess"]
    sessions_max = metrics.get("maxsess")

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
