#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    Metric,
    render,
    Result,
    Service,
    State,
)
from cmk.plugins.postgres import lib as postgres

# OLD FORMAT - with idle filter
# <<<postgres_connections:sep(59)>>>
# [databases_start]
# postgres
# app
# app_test
# [databases_end]
# datname;current;mc
# app;0;100
# app_test;0;100
# postgres;1;100
# template0;0;100
# template1;0;100

# NEW FORMAT - without idle filter
# <<<postgres_connections:sep(59)>>>
# [databases_start]
# postgres
# app
# app_test
# [databases_end]
# datname;current;mc;state
# app;2;100;idle
# app_test;0;100;
# postgres;1;100;active
# template0;0;100;
# template1;0;100;

# instances
# <<<postgres_bloat>>>
# [[[foobar]]]
# [databases_start]
# postgres
# testdb
# [databases_end]
# ...


def _transform_params(params: Mapping[str, Any]) -> dict[str, Any]:
    # Transform old params: previously the levels referred to active connections only
    transformed_params = dict(params)
    for old_level in ("levels_abs", "levels_perc"):
        if old_level in transformed_params:
            transformed_params[f"{old_level}_active"] = transformed_params[old_level]

    return transformed_params


def discover_postgres_connections(section: postgres.Section) -> DiscoveryResult:
    for db in section:
        yield Service(item=db)


def check_postgres_connections(
    item: str, params: Mapping[str, Any], section: postgres.Section
) -> CheckResult:
    if item not in section:
        # In case of missing information we assume that the login into
        # the database has failed and we simply skip this check. It won't
        # switch to UNKNOWN, but will get stale.
        raise IgnoreResultsError("Login into database failed")

    transformed_params = _transform_params(params)

    database = section[item]
    if len(database) == 0:
        for connection_type in ("active", "idle"):
            warn, crit = transformed_params.get(f"levels_abs_{connection_type}", (0, 0))
            yield Result(state=State.OK, summary=f"No {connection_type} connections")
            yield Metric(
                f"{connection_type}_connections",
                0,
                levels=(warn, crit),
                boundaries=(0, 0),
            )
        return

    database_connections = database[0]
    # New agent output differentiates between active and idle connections.
    # Previously, only number of active connections were sent
    has_active_and_idle = all(key in database_connections.keys() for key in ("active", "idle"))
    maximum = float(database_connections["mc"])

    connections = {
        "active": (
            database_connections["active"]
            if has_active_and_idle
            else database_connections["current"]
        ),
        "idle": database_connections["idle"] if has_active_and_idle else None,
    }

    for connection_type in ("active", "idle"):
        current = connections.get(connection_type)

        if not current:
            continue
        current_f = float(current)

        used_perc = current_f / maximum * 100

        warn, crit = transformed_params.get(f"levels_abs_{connection_type}", (None, None))
        yield from check_levels_v1(
            current_f,
            metric_name=f"{connection_type}_connections",
            levels_upper=(warn, crit) if warn is not None else None,
            render_func=lambda v: str(int(v)),
            label=f"Used {connection_type} connections",
            boundaries=(0, maximum),
        )

        warn, crit = transformed_params[f"levels_perc_{connection_type}"]
        yield from check_levels_v1(
            used_perc,
            levels_upper=(warn, crit),
            render_func=render.percent,
            label=f"Used {connection_type} percentage",
        )


agent_section_postgres_connections = AgentSection(
    name="postgres_connections",
    parse_function=postgres.parse_dbs,
)


check_plugin_postgres_connections = CheckPlugin(
    name="postgres_connections",
    service_name="PostgreSQL Connections %s",
    discovery_function=discover_postgres_connections,
    check_function=check_postgres_connections,
    check_ruleset_name="db_connections",
    check_default_parameters={
        "levels_perc_active": (80.0, 90.0),  # Levels at 80%/90% of maximum
        "levels_perc_idle": (80.0, 90.0),  # Levels at 80%/90% of maximum
    },
)
