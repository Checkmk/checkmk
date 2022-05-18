#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping, NamedTuple

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    check_levels,
    register,
    render,
    Result,
    Service,
    State,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)


class SansymphonyPool(NamedTuple):
    name: str
    percent_allocated: float
    status: str
    cache_mode: str
    pool_type: str


Section = Mapping[str, SansymphonyPool]


def parse_sansymphony_pool(string_table: StringTable) -> Section:
    return {
        name: SansymphonyPool(
            name=name,
            percent_allocated=float(percent_allocated),
            status=status,
            cache_mode=cache_mode,
            pool_type=type_,
        )
        for name, percent_allocated, status, cache_mode, type_ in string_table
    }


register.agent_section(
    name="sansymphony_pool",
    parse_function=parse_sansymphony_pool,
)


def discover_sansymphony_pool(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_sansymphony_pool(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    if (pool := section.get(item)) is None:
        return

    if pool.status == "Running" and pool.cache_mode == "ReadWrite":
        state = State.OK
    elif pool.status == "Running" and pool.cache_mode != "ReadWrite":
        state = State.WARN
    else:
        state = State.CRIT
    yield Result(
        state=state,
        summary=f"{pool.pool_type} pool {pool.name} is {pool.status}, its cache is in {pool.cache_mode} mode",
    )

    yield from check_levels(
        value=pool.percent_allocated,
        metric_name="pool_allocation",
        levels_upper=params["allocated_pools_percentage_upper"],
        render_func=render.percent,
        label="Pool allocation",
        boundaries=(0, 100),
    )


register.check_plugin(
    name="sansymphony_pool",
    discovery_function=discover_sansymphony_pool,
    check_function=check_sansymphony_pool,
    service_name="Sansymphony Pool %s",
    check_ruleset_name="sansymphony_pool",
    check_default_parameters={"allocated_pools_percentage_upper": (80.0, 90.0)},
)
