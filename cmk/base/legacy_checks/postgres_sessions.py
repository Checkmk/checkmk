#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

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


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import IgnoreResultsError

check_info = {}


def parse_postgres_sessions(string_table):
    parsed = {}
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


def discover_postgres_sessions(parsed):
    return [(db, {}) for db, dbinfo in parsed.items() if dbinfo]


def check_postgres_sessions(item, params, parsed):
    if item not in parsed:
        # In case of missing information we assume that the login into
        # the database has failed and we simply skip this check. It won't
        # switch to UNKNOWN, but will get stale.
        raise IgnoreResultsError("Login into database failed")

    data = parsed[item]
    idle = data["total"]
    running = data["running"]
    total = idle + running

    for key, val in [
        ("total", total),
        ("running", running),
    ]:
        infotext = f"{key.title()}: {val}"
        warn, crit = params.get(key, (None, None))
        state = 0
        if crit is not None and val >= crit:
            state = 2
        elif warn is not None and val >= warn:
            state = 1
        if state:
            infotext += f" (warn/crit at {warn}/{crit})"
        yield state, infotext, [(key, val, warn, crit)]


check_info["postgres_sessions"] = LegacyCheckDefinition(
    name="postgres_sessions",
    parse_function=parse_postgres_sessions,
    service_name="PostgreSQL Daemon Sessions %s",
    discovery_function=discover_postgres_sessions,
    check_function=check_postgres_sessions,
    check_ruleset_name="postgres_instance_sessions",
)
