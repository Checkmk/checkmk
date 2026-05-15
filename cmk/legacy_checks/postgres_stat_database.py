#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<postgres_stat_database>>>
# datid datname numbackends xact_commit xact_rollback blks_read blks_hit tup_returned tup_fetched tup_inserted tup_updated tup_deleted
# 1 template1 0 0 0 0 0 0 0 0 0 0
# 11563 template0 0 0 0 0 0 0 0 0 0 0
# 11564 postgres 2 568360 17 811 8855508 157949341 879922 0 0 0
# 16385 foobardb 7 43619118 262 3589 838098632 854602076 441785363 8298 602481 2806


import time
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    IgnoreResultsError,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)

Section = Mapping[str, Mapping[str, Any]]


def parse_postgres_stat_database(string_table: StringTable) -> Section:
    if len(string_table) == 0:
        return {}
    parsed: dict[str, dict[str, Any]] = {}
    instance_name = ""
    headers: list[str] = []
    for line in string_table:
        if line[0].startswith("[[[") and line[0].endswith("]]]"):
            instance_name = line[0][3:-3].upper()
            continue
        if line[0] == "datid" and line[1] == "datname":
            headers = line
            continue
        # All values other than datid and datname must be int
        row: dict[str, Any] = {
            k: int(v) if v else v for k, v in zip(headers, line) if k not in ("datid", "datname")
        }
        # datid should be an oid, which should be an int, but that may not be guaranteed
        # when the data entry is empty, we keep it as empty. Might have to change this to a default value (0) if issues come up.
        row["datid"] = line[0]
        # https://www.postgresql.org/message-id/CABUevEzMHzdAQjvpWO6eGSZeg8FKmLLPhdwVoqaOXR8VWnyd8w%40mail.gmail.com
        datname = line[1] if line[1] else "access_to_shared_objects"
        if instance_name:
            db_name = f"{instance_name}/{datname}"
        else:
            db_name = datname

        parsed[db_name] = row

    return parsed


# Create a check for all databases that have seen at least
# one commit in their live.
def discover_postgres_stat_database(section: Section) -> DiscoveryResult:
    for k in section:
        if section[k]["xact_commit"] > 0:
            yield Service(item=k)


def discover_postgres_stat_database_size(section: Section) -> DiscoveryResult:
    # https://www.postgresql.org/docs/current/monitoring-stats.html#MONITORING-PG-STAT-DATABASE-VIEW
    # > datid: OID of this database, or 0 for objects belonging to a shared relation
    # shared relations don't have a size, so we don't want to discover them.
    for k in section:
        if section[k]["xact_commit"] > 0 and section[k]["datid"] != "0":
            yield Service(item=k)


def check_postgres_stat_database(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if item not in section:
        yield Result(state=State.UNKNOWN, summary="Database not found")
        return

    stats = section[item]
    status = State.OK
    infos = []
    metrics: list[Metric] = []
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
                status = State.CRIT
                infos[-1] += "(!!)"
            elif rate >= warn:
                status = State.worst(status, State.WARN)
                infos[-1] += "(!)"
        else:
            warn, crit = None, None
        metrics.append(Metric(what, rate, levels=(warn, crit) if warn is not None else None))
    yield Result(state=status, summary=", ".join(infos))
    yield from metrics


agent_section_postgres_stat_database = AgentSection(
    name="postgres_stat_database",
    parse_function=parse_postgres_stat_database,
)


check_plugin_postgres_stat_database = CheckPlugin(
    name="postgres_stat_database",
    service_name="PostgreSQL DB %s Statistics",
    discovery_function=discover_postgres_stat_database,
    check_function=check_postgres_stat_database,
    check_ruleset_name="postgres_stat_database",
    check_default_parameters={},
)


def check_postgres_stat_database_size(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if item not in section:
        # In case of missing information we assume that the login into
        # the database has failed and we simply skip this check. It won't
        # switch to UNKNOWN, but will get stale.
        raise IgnoreResultsError("Login into database failed")
    levels = params.get("database_size")
    stats = section[item]
    size = stats["datsize"]

    if size in ["", None]:
        yield Result(state=State.WARN, summary="Database size is not available.")
        return

    yield from check_levels_v1(
        size,
        metric_name="size",
        levels_upper=levels,
        render_func=render.bytes,
        label="Size",
    )


check_plugin_postgres_stat_database_size = CheckPlugin(
    name="postgres_stat_database_size",
    service_name="PostgreSQL DB %s Size",
    sections=["postgres_stat_database"],
    discovery_function=discover_postgres_stat_database_size,
    check_function=check_postgres_stat_database_size,
    check_ruleset_name="postgres_stat_database",
    check_default_parameters={},
)
