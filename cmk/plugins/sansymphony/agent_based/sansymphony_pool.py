#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any, NamedTuple

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.df import (
    Bytes,
    check_filesystem_levels,
    FILESYSTEM_DEFAULT_LEVELS,
    MAGIC_FACTOR_DEFAULT_PARAMS,
)


class Usage(NamedTuple):
    pool_size: Bytes
    allocated_space: Bytes
    available_space: Bytes


class SimpleUsage(NamedTuple):
    percent_allocated: float


class SansymphonyPool(NamedTuple):
    name: str
    status: str
    cache_mode: str
    pool_type: str
    usage_stats: SimpleUsage | Usage


Section = Mapping[str, SansymphonyPool]


def parse_sansymphony_pool(string_table: StringTable) -> Section:
    return {
        name: SansymphonyPool(
            name=name,
            status=status,
            cache_mode=cache_mode,
            pool_type=type_,
            usage_stats=SimpleUsage(
                percent_allocated=float(percent_allocated),
            ),
        )
        for name, percent_allocated, status, cache_mode, type_ in string_table[:5]
    }


agent_section_sansymphony_pool = AgentSection(
    name="sansymphony_pool",
    parse_function=parse_sansymphony_pool,
)


def parse_sansymphony_pool_v2(string_table: StringTable) -> Section:
    # introduced in Checkmk 2.2.0i1
    return {
        name: SansymphonyPool(
            name=name,
            status=status,
            cache_mode=cache_mode,
            pool_type=type_,
            usage_stats=Usage(
                allocated_space=Bytes(int(allocated_space)),
                available_space=Bytes(int(available_space)),
                pool_size=Bytes(int(pool_size)),
            ),
        )
        for name, _, status, cache_mode, type_, allocated_space, available_space, pool_size in string_table
    }


agent_section_sansymphony_pool_v2 = AgentSection(
    name="sansymphony_pool_v2",
    parsed_section_name="sansymphony_pool",
    parse_function=parse_sansymphony_pool_v2,
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

    if isinstance(pool.usage_stats, SimpleUsage):
        # sansymphony_pool
        yield from check_levels_v1(
            value=pool.usage_stats.percent_allocated,
            metric_name="pool_allocation",
            levels_upper=params["levels"],
            render_func=render.percent,
            label="Used",
            boundaries=(0, 100),
        )
        if "magic" in params:
            yield Result(
                state=State.WARN,
                summary="Magic factor is not available (see check details)",
                details=(
                    "Magic factor is not available with the current version of the agent plugin. "
                    "Please upgrade it to version 2.2.0 or higher, or disable magic factor for this service."
                ),
            )
        return

    # sansymphony_pool_v2
    pool_size_mb = pool.usage_stats.pool_size / 1024.0**2
    yield from check_filesystem_levels(
        filesystem_size=pool_size_mb,
        allocatable_filesystem_size=pool_size_mb,
        free_space=pool.usage_stats.available_space / 1024.0**2,
        used_space=pool.usage_stats.allocated_space / 1024.0**2,
        params=params,
    )


check_plugin_sansymphony_pool = CheckPlugin(
    name="sansymphony_pool",
    discovery_function=discover_sansymphony_pool,
    check_function=check_sansymphony_pool,
    service_name="Sansymphony Pool %s",
    check_ruleset_name="sansymphony_pool",
    check_default_parameters={
        **FILESYSTEM_DEFAULT_LEVELS,
        **MAGIC_FACTOR_DEFAULT_PARAMS,
    },
)
