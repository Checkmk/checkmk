#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
)
from cmk.plugins.postgres import lib as postgres

# <<<postgres_locks>>>
# [databases_start]
# postgres
# zweitedb
# testdb
# datenbank
# [databases_end]
# datname;granted;mode
# postgres;t;AccessShareLock
# zweitedb;;
# template1;;
# datenbank;;

# instance
# <<<postgres_locks>>>
# [[[foobar]]]
# [databases_start]
# postgres
# testdb
# [databases_end]
# ...


def discover_postgres_locks(section: postgres.Section) -> DiscoveryResult:
    for entry in section:
        yield Service(item=entry)


def check_postgres_locks(
    item: str, params: Mapping[str, Any], section: postgres.Section
) -> CheckResult:
    if item not in section:
        # In case of missing information we assume that the login into
        # the database has failed and we simply skip this check. It won't
        # switch to UNKNOWN, but will get stale.
        raise IgnoreResultsError("Login into database failed")

    locks: dict[str, int] = {}
    for element in section[item]:
        if element["granted"]:
            locks.setdefault(element["mode"], 0)
            locks[element["mode"]] += 1

    shared_locks = locks.get("AccessShareLock", 0)
    yield Result(state=State.OK, summary=f"Access Share Locks {shared_locks}")
    yield Metric("shared_locks", shared_locks)

    if "levels_shared" in params:
        warn, crit = params["levels_shared"]
        if shared_locks >= crit:
            yield Result(state=State.CRIT, summary=f"too high (Levels at {warn}/{crit})")
        elif shared_locks >= warn:
            yield Result(state=State.WARN, summary=f"too high (Levels at {warn}/{crit})")

    exclusive_locks = locks.get("ExclusiveLock", 0)
    yield Result(state=State.OK, summary=f"Exclusive Locks {exclusive_locks}")
    yield Metric("exclusive_locks", exclusive_locks)
    if "levels_exclusive" in params:
        warn, crit = params["levels_exclusive"]
        if exclusive_locks >= crit:
            yield Result(state=State.CRIT, summary=f"too high (Levels at {warn}/{crit})")
        elif exclusive_locks >= warn:
            yield Result(state=State.WARN, summary=f"too high (Levels at {warn}/{crit})")


agent_section_postgres_locks = AgentSection(
    name="postgres_locks",
    parse_function=postgres.parse_dbs,
)


check_plugin_postgres_locks = CheckPlugin(
    name="postgres_locks",
    service_name="PostgreSQL Locks %s",
    discovery_function=discover_postgres_locks,
    check_function=check_postgres_locks,
    check_ruleset_name="postgres_locks",
    check_default_parameters={},
)
