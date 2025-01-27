#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import defaultdict
from collections.abc import Mapping
from enum import Enum
from typing import NamedTuple, NotRequired, TypedDict

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
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
from cmk.agent_based.v2.clusterize import make_node_notice_results


class CheckType(Enum):
    COUNT = "count"
    WAIT_TIME = "waittime"


class Params(TypedDict):
    waittime: NotRequired[tuple[float, float]]
    state: int
    ignore_waittypes: NotRequired[list[str]]


DEFAULT_PARAMETERS: Params = {
    "state": 2,
}

NO_BLOCKING_SESSIONS_MSG = "No blocking sessions"


class DBInstance(NamedTuple):
    session_id: str
    wait_type: str
    blocking_session_id: str
    wait_duration: float


def parse_mssql_blocked_sessions(string_table: StringTable) -> dict[str, list[DBInstance]]:
    parsed: dict[str, list[DBInstance]] = {}
    for line in string_table:
        if line[-1].startswith("ERROR:"):
            continue

        if len(line) in (1, 4):
            continue

        if len(line) == 2 and line[1] == NO_BLOCKING_SESSIONS_MSG:
            parsed.setdefault(line[0], [])
        elif len(line) == 5:
            inst, session_id, wait_duration_ms, wait_type, blocking_session_id = line
            parsed.setdefault(inst, []).append(
                DBInstance(
                    session_id,
                    wait_type,
                    blocking_session_id,
                    float(wait_duration_ms) / 1000,
                )
            )

    return parsed


def check_mssql_blocked_sessions(
    item: str, params: Params, section: dict[str, list[DBInstance]]
) -> CheckResult:
    if item == "":
        yield Result(
            state=State.UNKNOWN,
            summary="MSSQL agent plug-in prior to Checkmk version 1.6 is no longer supported. "
            "Please upgrade your agent plug-in to a newer version (see Werk 6140)",
        )
        return
    if (data := section.get(item)) is None:
        # Assume general connection problem to the database, which is reported
        # by the "X Instance" service and skip this check.
        raise IgnoreResultsError("Failed to retrieve data from database")
    if not data:
        yield Result(state=State.OK, summary=NO_BLOCKING_SESSIONS_MSG)
        return

    blocked_sessions_counter: defaultdict[str, int] = defaultdict(int)
    details: list[Result] = []
    warn, crit = params.get("waittime", (None, None))
    ignored_waittypes = set()
    waittypes_to_be_ignored = params.get("ignore_waittypes", [])
    # the default behaviour is that a single blocking session is changing the state of this check
    # (no timing levels are checked at all)
    check_type = CheckType.COUNT
    if crit is not None and warn is not None:
        # if levels are set, blocking sessions lower than the level will remain OK.
        check_type = CheckType.WAIT_TIME

    for db_inst in data:
        if db_inst.wait_type in waittypes_to_be_ignored:
            ignored_waittypes.add(db_inst.wait_type)
            continue

        (result,) = check_levels_v1(
            db_inst.wait_duration,
            levels_upper=params.get("waittime"),
            label=f"Session {db_inst.session_id} blocked by {db_inst.blocking_session_id}, Type: {db_inst.wait_type}, Wait",
            render_func=render.timespan,
        )
        details.append(result)
        blocked_sessions_counter[db_inst.session_id] += 1

    if blocked_sessions_counter:
        if check_type == CheckType.COUNT:
            state = State(params["state"])
        else:
            state = State.OK

        yield Result(
            state=state,
            summary="Summary: %s"
            % (
                ", ".join(
                    [
                        f"{k} blocked by {v} ID(s)"
                        for k, v in sorted(blocked_sessions_counter.items())
                    ]
                )
            ),
        )

        yield from details
    else:
        yield Result(state=State.OK, summary=NO_BLOCKING_SESSIONS_MSG)

    if ignored_waittypes:
        yield Result(
            state=State.OK, summary="Ignored wait types: %s" % ", ".join(ignored_waittypes)
        )


def discovery_mssql_blocked_sessions(section: dict[str, list[DBInstance]]) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def cluster_check_mssql_blocked_sessions(
    item: str, params: Params, section: Mapping[str, dict[str, list[DBInstance]] | None]
) -> CheckResult:
    for node_name, node_section in section.items():
        if not node_section:
            continue
        yield from make_node_notice_results(
            node_name,
            check_mssql_blocked_sessions(item, params, node_section),
        )


agent_section_mssql_blocked_sessions = AgentSection(
    name="mssql_blocked_sessions",
    parse_function=parse_mssql_blocked_sessions,
)

check_plugin_mssql_blocked_sessions = CheckPlugin(
    name="mssql_blocked_sessions",
    sections=["mssql_blocked_sessions"],
    service_name="MSSQL %s Blocked Sessions",
    discovery_function=discovery_mssql_blocked_sessions,
    check_function=check_mssql_blocked_sessions,
    cluster_check_function=cluster_check_mssql_blocked_sessions,
    check_default_parameters=DEFAULT_PARAMETERS,
    check_ruleset_name="mssql_instance_blocked_sessions",
)
