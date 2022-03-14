#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

from cmk.base.plugins.agent_based.utils import postgres

from .agent_based_api.v1 import (
    check_levels,
    get_value_store,
    IgnoreResults,
    register,
    render,
    Result,
    Service,
    State,
)

# <<<postgres_stats>>>
# [databases_start]
# postgres
# testdb
# datenbank
# [databases_end]
# datname;sname;tname;vtime;atime
# postgres;pg_catalog;pg_statistic;-1;-1
# postgres;pg_catalog;pg_type;-1;-1
# postgres;pg_catalog;pg_authid;-1;-1
# postgres;pg_catalog;pg_attribute;-1;-1


def discover_postgres_stats(section):
    for item in section:
        yield Service(item=f"VACUUM {item}")
        yield Service(item=f"ANALYZE {item}")


def _check_never_checked(text, never_checked, params, value_store, now):
    state_key = "last-time-all-checked"

    if not never_checked:
        value_store[state_key] = now
        yield Result(state=State.OK, summary="No never checked tables")
        return

    count = len(never_checked)
    cutoff_hint = " (first 3 shown)" if count > 3 else ""
    yield Result(
        state=State.OK,
        summary=f"{count} tables were never {text}: {' / '.join(never_checked[:3])}{cutoff_hint}",
        details=f"{count} tables were never {text}: {' / '.join(never_checked)}",
    )

    last_ts = value_store.get(state_key)
    if last_ts is None:
        value_store[state_key] = now
        return

    yield from check_levels(
        now - last_ts,
        levels_upper=params.get("never_analyze_vacuum"),
        render_func=render.timespan,
        label=f"Never {text} tables for",
    )


def check_postgres_stats(item, params, section):
    yield from _check_postgres_stats(
        item=item,
        params=params,
        section=section,
        value_store=get_value_store(),
        now=time.time(),
    )


def _check_postgres_stats(*, item, params, section, value_store, now):
    item_type, database = item.split(" ", 1)
    data = section.get(database)

    if data is None:
        # In case of missing information we assume that the login into
        # the database has failed and we simply skip this check. It won't
        # switch to UNKNOWN, but will get stale.
        yield IgnoreResults("Login into database failed")
        return

    stats_field = f"{item_type[0].lower()}time"
    text = f"{item_type.lower().strip('e')}ed"

    times_and_names = [
        (int(table[stats_field]) if table[stats_field] else -1, table["tname"])
        for table in data
        if table["sname"] != "pg_catalog"
    ]
    oldest_element = min(((t, n) for t, n in times_and_names if t != -1), default=None)
    never_checked = [n for t, n in times_and_names if t == -1]

    if oldest_element:
        oldest_time, oldest_name = oldest_element
        yield Result(state=State.OK, summary=f"Table: {oldest_name}")
        yield from check_levels(
            now - oldest_time,
            levels_upper=params.get(f"last_{item_type.lower()}"),
            render_func=render.timespan,
            label=f"Not {text} for",
        )

    yield from _check_never_checked(text, never_checked, params, value_store, now)


register.agent_section(
    name="postgres_stats",
    parse_function=postgres.parse_dbs,
)

register.check_plugin(
    name="postgres_stats",
    service_name="PostgreSQL %s",
    discovery_function=discover_postgres_stats,
    check_function=check_postgres_stats,
    check_ruleset_name="postgres_maintenance",
    check_default_parameters={
        "never_analyze_vacuum": (0, 1000 * 365 * 24 * 3600),
    },
)
