#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="possibly-undefined"

# <<<postgres_stat_database>>>
# datid datname numbackends xact_commit xact_rollback blks_read blks_hit tup_returned tup_fetched tup_inserted tup_updated tup_deleted
# 1 template1 0 0 0 0 0 0 0 0 0 0
# 11563 template0 0 0 0 0 0 0 0 0 0 0
# 11564 postgres 2 568360 17 811 8855508 157949341 879922 0 0 0
# 16385 foobardb 7 43619118 262 3589 838098632 854602076 441785363 8298 602481 2806


import time

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import get_rate, get_value_store, IgnoreResultsError, render

check_info = {}


def parse_postgres_stat_database(string_table):
    if len(string_table) == 0:
        return {}
    parsed = {}
    instance_name = ""
    for line in string_table:
        if line[0].startswith("[[[") and line[0].endswith("]]]"):
            instance_name = line[0][3:-3].upper()
            continue
        if line[0] == "datid" and line[1] == "datname":
            headers = line
            continue
        # All values other than datid and datname must be int
        row = {
            k: int(v) if v else v for k, v in zip(headers, line) if k not in ("datid", "datname")
        }
        # datid should be an oid, which should be an int, but that may not be guaranteed
        # when the data entry is empty, we keep it as empty. Might have to change this to a default value (0) if issues come up.
        row["datid"] = line[0]
        datname = (
            line[1] if line[1] else "access_to_shared_objects"
        )  # https://www.postgresql.org/message-id/CABUevEzMHzdAQjvpWO6eGSZeg8FKmLLPhdwVoqaOXR8VWnyd8w%40mail.gmail.com
        if instance_name:
            db_name = f"{instance_name}/{datname}"
        else:
            db_name = datname

        parsed[db_name] = row

    return parsed


# Create a check for all databases that have seen at least
# one commit in their live.
def discover_postgres_stat_database(parsed):
    return [(k, {}) for k in parsed if parsed[k]["xact_commit"] > 0]


def discover_postgres_stat_database_size(parsed):
    # https://www.postgresql.org/docs/current/monitoring-stats.html#MONITORING-PG-STAT-DATABASE-VIEW
    # > datid: OID of this database, or 0 for objects belonging to a shared relation
    # shared relations don't have a size, so we don't want to discover them.
    return [(k, {}) for k in parsed if parsed[k]["xact_commit"] > 0 and parsed[k]["datid"] != "0"]


def check_postgres_stat_database(item, params, parsed):
    if item not in parsed:
        return (3, "Database not found")

    stats = parsed[item]
    status = 0
    infos = []
    perfdata = []
    this_time = time.time()
    for what, title in [
        ("blks_read", "Blocks Read"),
        ("tup_fetched", "Fetches"),
        ("xact_commit", "Commits"),
        ("tup_deleted", "Deletes"),
        ("tup_updated", "Updates"),
        ("tup_inserted", "Inserts"),
    ]:
        rate = get_rate(
            get_value_store(),
            f"postgres_stat_database.{item}.{what}",
            this_time,
            stats[what],
            raise_overflow=True,
        )
        infos.append(f"{title}: {rate:.2f}/s")
        if what in params:
            warn, crit = params[what]
            if rate >= crit:
                status = 2
                infos[-1] += "(!!)"
            elif rate >= warn:
                status = max(status, 1)
                infos[-1] += "(!)"
        else:
            warn, crit = None, None
        perfdata.append((what, rate, warn, crit))
    return (status, ", ".join(infos), perfdata)


check_info["postgres_stat_database"] = LegacyCheckDefinition(
    name="postgres_stat_database",
    parse_function=parse_postgres_stat_database,
    service_name="PostgreSQL DB %s Statistics",
    discovery_function=discover_postgres_stat_database,
    check_function=check_postgres_stat_database,
    check_ruleset_name="postgres_stat_database",
)


def check_postgres_stat_database_size(item, params, parsed):
    if item not in parsed:
        # In case of missing information we assume that the login into
        # the database has failed and we simply skip this check. It won't
        # switch to UNKNOWN, but will get stale.
        raise IgnoreResultsError("Login into database failed")
    levels = params.get("database_size")
    stats = parsed[item]
    size = stats["datsize"]

    if size in ["", None]:
        yield (1, "Database size is not available.")
        return

    yield check_levels(
        size,
        "size",
        levels,
        human_readable_func=render.bytes,
        infoname="Size",
    )


check_info["postgres_stat_database.size"] = LegacyCheckDefinition(
    name="postgres_stat_database_size",
    service_name="PostgreSQL DB %s Size",
    sections=["postgres_stat_database"],
    discovery_function=discover_postgres_stat_database_size,
    check_function=check_postgres_stat_database_size,
    check_ruleset_name="postgres_stat_database",
)
