#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, Optional

from .agent_based_api.v1 import IgnoreResults, register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from .utils import postgres

# <<<postgres_query_duration>>>
# [databases_start]
# postgres
# testdb
# datenbank
# [databases_end]
# datname;datid;usename;client_addr;state;seconds;pid;current_query
# postgres;12068;postgres;;active;0;12631;SELECT datname, datid, usename, ....

# instance
# <<<postgres_query_duration>>>
# [[[foobar]]]
# [databases_start]
# postgres
# testdb
# [databases_end]
# ...


def discover_postgres_query_duration(section: postgres.Section) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_postgres_query_duration(item: str, section: postgres.Section) -> CheckResult:
    data = section.get(item)
    if data is None:
        # In case of missing information we assume that the login into
        # the database has failed and we simply skip this check. It won't
        # switch to UNKNOWN, but will get stale.
        yield IgnoreResults("Login into database failed")
        return

    if not data:
        yield Result(state=State.OK, summary="No queries running")
        return

    query = max(data, key=lambda q: int(q["seconds"]))

    yield Result(state=State.OK, summary=f"Longest query: {query['seconds']} seconds")

    if query["usename"]:
        Result(state=State.OK, summary=f"Username: {query['usename']}")

    if query["client_addr"]:
        yield Result(state=State.OK, summary=f"Client: {query['client_addr']}")

    if query["state"].lower() != "active":
        yield Result(state=State.OK, summary=f"Query state: {query['state']}")

    yield Result(state=State.OK, summary=f"PID: {query['pid']}")
    yield Result(state=State.OK, summary=f"Query: {query['current_query']}")


def cluster_check_postgres_query_duration(
    item: str,
    section: Mapping[str, Optional[postgres.Section]],
) -> CheckResult:
    data = [
        d
        for d in (
            node_section.get(item) for node_section in section.values() if node_section is not None
        )
        if d is not None
    ]
    yield from check_postgres_query_duration(
        item, {item: [x for d in data for x in d]} if data else {}
    )


register.agent_section(
    name="postgres_query_duration",
    parse_function=postgres.parse_dbs,
)

register.check_plugin(
    name="postgres_query_duration",
    service_name="PostgreSQL Query Duration %s",
    discovery_function=discover_postgres_query_duration,
    check_function=check_postgres_query_duration,
    cluster_check_function=cluster_check_postgres_query_duration,
)
