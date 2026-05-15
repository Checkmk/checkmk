#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<postgres_conn_time>>>
# 0.063

# instances
# <<<postgres_conn_time>>>
# [[[foobar]]]
# 0.063


from collections.abc import Mapping

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

Section = Mapping[str, float]


def parse_postgres_conn_time(string_table: StringTable) -> Section:
    parsed: dict[str, float] = {}
    instance_name = ""
    for line in string_table:
        if line[0].startswith("[[[") and line[0].endswith("]]]"):
            instance_name = line[0][3:-3].upper()
            continue
        parsed.setdefault(instance_name, float(line[0]))
    return parsed


def discover_postgres_conn_time(section: Section) -> DiscoveryResult:
    for instance_name in section:
        yield Service(item=instance_name)


def check_postgres_conn_time(item: str, section: Section) -> CheckResult:
    if item in section:
        conn_time = section[item]
        yield Result(state=State.OK, summary=f"{conn_time} seconds")
        yield Metric("connection_time", conn_time)
        return

    # In case of missing information we assume that the login into
    # the database has failed and we simply skip this check. It won't
    # switch to UNKNOWN, but will get stale.
    raise IgnoreResultsError("Login into database failed")


agent_section_postgres_conn_time = AgentSection(
    name="postgres_conn_time",
    parse_function=parse_postgres_conn_time,
)


check_plugin_postgres_conn_time = CheckPlugin(
    name="postgres_conn_time",
    service_name="PostgreSQL Connection Time %s",
    discovery_function=discover_postgres_conn_time,
    check_function=check_postgres_conn_time,
)
