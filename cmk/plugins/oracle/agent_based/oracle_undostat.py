#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

# In cooperation with Thorsten Bruhns from OPITZ Consulting

# <<<oracle_undostat>>>
# TUX2 160 0 1081 300 0


import contextlib
from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)

from .liboracle import Error, is_instance_name, Ok, oracle_handle_ora_errors, Parsed

type Section = Mapping[str, Parsed[Sequence[int]]]


def parse_oracle_undostat(string_table: StringTable) -> Section:
    stats: dict[str, Sequence[int]] = {}
    errors: dict[str, str] = {}
    for line in string_table:
        match oracle_handle_ora_errors(line):
            case str() as message:
                errors.setdefault(line[0], message)
            case False:
                continue
            case None:
                if len(line) == 6:
                    with contextlib.suppress(ValueError):
                        stats[line[0]] = [int(v) for v in line[1:]]

    parsed: dict[str, Parsed[Sequence[int]]] = {
        sid: Ok(values) for sid, values in stats.items() if sid not in errors
    }
    for sid, message in errors.items():
        parsed[sid] = Error(message)
    return parsed


def discover_oracle_undostat(section: Section) -> DiscoveryResult:
    yield from (Service(item=sid) for sid in section if is_instance_name(sid))


def check_oracle_undostat(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    match section.get(item):
        case None:
            # In case of missing information we assume that the login into
            # the database has failed and we simply skip this check. It won't
            # switch to UNKNOWN, but will get stale.
            raise IgnoreResultsError("Login into database failed")
        case Error(message):
            yield Result(state=State.UNKNOWN, summary=message)
        case Ok(data):
            yield from _check_undostat(params, data)


def _check_undostat(params: Mapping[str, Any], data: Sequence[int]) -> CheckResult:
    activeblks, maxconcurrency, tuned_undoretention, maxquerylen, nospaceerrcnt = data
    warn, crit = params["levels"]

    yield from check_levels(
        tuned_undoretention,
        levels_lower=("no_levels", None) if tuned_undoretention == -1 else ("fixed", (warn, crit)),
        render_func=str if tuned_undoretention == -1 else render.timespan,
        label="Undo retention",
    )

    if tuned_undoretention >= 0:
        yield Result(state=State.OK, summary="Active undo blocks: %d" % activeblks)

    yield Result(state=State.OK, summary="Max concurrent transactions: %d" % maxconcurrency)
    yield Result(state=State.OK, summary="Max querylen: %s" % render.timespan(maxquerylen))
    state_errcnt = State(params["nospaceerrcnt_state"]) if nospaceerrcnt else State.OK
    yield Result(state=state_errcnt, summary="Space errors: %d" % nospaceerrcnt)

    yield Metric("activeblk", activeblks)
    yield Metric("transconcurrent", maxconcurrency)
    # lower levels are unorthodox here (at least), but we keep it for compatibility (for now)
    yield Metric("tunedretention", tuned_undoretention, levels=(warn, crit))
    yield Metric("querylen", maxquerylen)
    yield Metric("nonspaceerrcount", nospaceerrcnt)


agent_section_oracle_undostat = AgentSection(
    name="oracle_undostat",
    parse_function=parse_oracle_undostat,
)

check_plugin_oracle_undostat = CheckPlugin(
    name="oracle_undostat",
    service_name="ORA %s Undo Retention",
    discovery_function=discover_oracle_undostat,
    check_function=check_oracle_undostat,
    check_ruleset_name="oracle_undostat",
    check_default_parameters={
        "levels": (600, 300),
        "nospaceerrcnt_state": 2,
    },
)
