#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping, NamedTuple, Optional

from .agent_based_api.v1 import IgnoreResultsError, register, render, Result, Service, State
from .agent_based_api.v1.clusterize import make_node_notice_results
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable

DEFAULT_PARAMETERS = {
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

        if len(line) == 1 and line[0] == NO_BLOCKING_SESSIONS_MSG:
            parsed.setdefault("", [])
        elif len(line) == 2 and line[1] == NO_BLOCKING_SESSIONS_MSG:
            parsed.setdefault(line[0], [])
        elif len(line) == 4:
            session_id, wait_duration_ms, wait_type, blocking_session_id = line
            parsed.setdefault("", []).append(
                DBInstance(
                    session_id,
                    wait_type,
                    blocking_session_id,
                    float(wait_duration_ms) / 1000,
                )
            )
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


def check_mssql_blocked_sessions(  # pylint: disable=too-many-branches
    item: str, params: dict[str, Any], section: dict[str, list[DBInstance]]
) -> CheckResult:
    if item is None:
        item = ""

    data = section.get(item)
    if data is None:
        # Assume general connection problem to the database, which is reported
        # by the "X Instance" service and skip this check.
        raise IgnoreResultsError("Failed to retrieve data from database")
    if not data:
        yield Result(state=State.OK, summary=NO_BLOCKING_SESSIONS_MSG)
        return

    summary: dict[str, int] = {}
    details: list[Result] = []
    warn, crit = params.get("waittime", (None, None))
    ignored_waittypes = set()
    waittypes_to_be_ignored = params.get("ignore_waittypes", [])

    for db_inst in data:
        if db_inst.wait_type in waittypes_to_be_ignored:
            ignored_waittypes.add(db_inst.wait_type)
            continue

        if crit is not None and db_inst.wait_duration >= crit:
            state = State.CRIT
        elif warn is not None and db_inst.wait_duration >= warn:
            state = State.WARN
        else:
            state = State.OK

        summary.setdefault(db_inst.session_id, 0)
        summary[db_inst.session_id] += 1
        details.append(
            Result(
                state=state,
                summary="Session %s blocked by %s (Type: %s, Wait: %s)"
                % (
                    db_inst.session_id,
                    db_inst.blocking_session_id,
                    db_inst.wait_type,
                    render.timespan(db_inst.wait_duration),
                ),
            )
        )

    if summary:
        yield Result(
            state=State(params["state"]),
            summary="Summary: %s"
            % (", ".join(["%s blocked by %s ID(s)" % (k, v) for k, v in sorted(summary.items())])),
        )

        max_state = State.worst(*(r.state for r in details))
        if max_state in {State.CRIT, State.WARN}:
            yield Result(
                state=max_state,
                summary="At least one session above thresholds (warn/crit at %s/%s)"
                % (
                    render.timespan(warn),
                    render.timespan(crit),
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
    item: str, params: dict[str, Any], section: Mapping[str, Optional[dict[str, list[DBInstance]]]]
) -> CheckResult:
    for node_name, node_section in section.items():
        if not node_section:
            continue
        yield from make_node_notice_results(
            node_name,
            check_mssql_blocked_sessions(item, params, node_section),
        )


register.agent_section(
    name="mssql_blocked_sessions",
    parse_function=parse_mssql_blocked_sessions,
)

register.check_plugin(
    name="mssql_blocked_sessions",
    sections=["mssql_blocked_sessions"],
    service_name="MSSQL %s Blocked Sessions",
    discovery_function=discovery_mssql_blocked_sessions,
    check_function=check_mssql_blocked_sessions,
    cluster_check_function=cluster_check_mssql_blocked_sessions,
    check_default_parameters=DEFAULT_PARAMETERS,
    check_ruleset_name="mssql_instance_blocked_sessions",
)
