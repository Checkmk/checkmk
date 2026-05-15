#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<postgres_sessions>>>
# f 1
# t 4

# instance
# <<<postgres_locks>>>
# [[[foobar]]]
# f 1
# t 4

# t -> idle sessions, f -> active sessions
# Note: one (or both?) lines might be missing. They will never show 0.


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)

Section = Mapping[str, Mapping[str, int]]


def parse_postgres_sessions(string_table: StringTable) -> Section:
    parsed: dict[str, dict[str, int]] = {}
    instance_name = ""
    for line in string_table:
        if line[0].startswith("[[[") and line[0].endswith("]]]"):
            instance_name = line[0][3:-3].upper()
            continue
        instance = parsed.setdefault(
            instance_name,
            {
                "total": 0,
                "running": 0,
            },
        )
        if line[0].startswith("t"):
            instance["total"] = int(line[1])
        elif line[0].startswith("f"):
            instance["running"] = int(line[1])
    return parsed


def discover_postgres_sessions(section: Section) -> DiscoveryResult:
    for db, dbinfo in section.items():
        if dbinfo:
            yield Service(item=db)


def check_postgres_sessions(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if item not in section:
        # In case of missing information we assume that the login into
        # the database has failed and we simply skip this check. It won't
        # switch to UNKNOWN, but will get stale.
        raise IgnoreResultsError("Login into database failed")

    data = section[item]
    idle = data["total"]
    running = data["running"]
    total = idle + running

    for key, val in [
        ("total", total),
        ("running", running),
    ]:
        infotext = f"{key.title()}: {val}"
        warn, crit = params.get(key, (None, None))
        state = State.OK
        if crit is not None and val >= crit:
            state = State.CRIT
        elif warn is not None and val >= warn:
            state = State.WARN
        if state is not State.OK:
            infotext += f" (warn/crit at {warn}/{crit})"
        yield Result(state=state, summary=infotext)
        yield Metric(
            key, val, levels=(warn, crit) if warn is not None and crit is not None else None
        )


agent_section_postgres_sessions = AgentSection(
    name="postgres_sessions",
    parse_function=parse_postgres_sessions,
)


check_plugin_postgres_sessions = CheckPlugin(
    name="postgres_sessions",
    service_name="PostgreSQL Daemon Sessions %s",
    discovery_function=discover_postgres_sessions,
    check_function=check_postgres_sessions,
    check_ruleset_name="postgres_instance_sessions",
    check_default_parameters={},
)
