#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import IgnoreResultsError
from cmk.plugins.postgres import lib as postgres

check_info = {}

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


def discover_postgres_locks(parsed):
    for entry in parsed:
        yield entry, {}


def check_postgres_locks(item, params, parsed):
    if item not in parsed:
        # In case of missing information we assume that the login into
        # the database has failed and we simply skip this check. It won't
        # switch to UNKNOWN, but will get stale.
        raise IgnoreResultsError("Login into database failed")

    locks = {}
    for element in parsed[item]:
        if element["granted"]:
            locks.setdefault(element["mode"], 0)
            locks[element["mode"]] += 1

    shared_locks = locks.get("AccessShareLock", 0)
    yield 0, "Access Share Locks %d" % shared_locks, [("shared_locks", shared_locks)]

    if "levels_shared" in params:
        warn, crit = params["levels_shared"]
        if shared_locks >= crit:
            yield 2, "too high (Levels at %d/%d)" % (warn, crit)
        elif shared_locks >= warn:
            yield 1, "too high (Levels at %d/%d)" % (warn, crit)

    exclusive_locks = locks.get("ExclusiveLock", 0)
    yield 0, "Exclusive Locks %d" % exclusive_locks, [("exclusive_locks", exclusive_locks)]
    if "levels_exclusive" in params:
        warn, crit = params["levels_exclusive"]
        if exclusive_locks >= crit:
            yield 2, "too high (Levels at %d/%d)" % (warn, crit)
        elif exclusive_locks >= warn:
            yield 1, "too high (Levels at %d/%d)" % (warn, crit)


check_info["postgres_locks"] = LegacyCheckDefinition(
    name="postgres_locks",
    parse_function=postgres.parse_dbs,
    service_name="PostgreSQL Locks %s",
    discovery_function=discover_postgres_locks,
    check_function=check_postgres_locks,
    check_ruleset_name="postgres_locks",
)
