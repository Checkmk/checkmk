#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.collection.agent_based.sansymphony_pool import (
    check_sansymphony_pool,
    discover_sansymphony_pool,
    parse_sansymphony_pool,
    parse_sansymphony_pool_v2,
    SansymphonyPool,
    SimpleUsage,
    Usage,
)
from cmk.plugins.lib.df import Bytes, FILESYSTEM_DEFAULT_LEVELS, MAGIC_FACTOR_DEFAULT_PARAMS


def test_parse_sansymphony_pool_no_agent_output() -> None:
    assert parse_sansymphony_pool([]) == {}


def test_parse_sansymphony_pool() -> None:
    assert parse_sansymphony_pool(
        [
            [
                "Disk_pool_1",
                "57",
                "Running",
                "ReadWrite",
                "Dynamic",
            ]
        ]
    ) == {
        "Disk_pool_1": SansymphonyPool(
            name="Disk_pool_1",
            usage_stats=SimpleUsage(percent_allocated=57.0),
            status="Running",
            cache_mode="ReadWrite",
            pool_type="Dynamic",
        ),
    }


def test_parse_sansymphony_pool_v2() -> None:
    assert parse_sansymphony_pool_v2(
        [
            [
                "Disk_pool_1",
                "57",
                "Running",
                "ReadWrite",
                "Dynamic",
                "800",
                "200",
                "1000",
            ]
        ]
    ) == {
        "Disk_pool_1": SansymphonyPool(
            name="Disk_pool_1",
            usage_stats=Usage(
                allocated_space=Bytes(800),
                available_space=Bytes(200),
                pool_size=Bytes(1000),
            ),
            status="Running",
            cache_mode="ReadWrite",
            pool_type="Dynamic",
        ),
    }


def test_discover_sansymphony_pool_no_agent_output() -> None:
    assert not list(discover_sansymphony_pool({}))


def test_discover_sansymphony_pool() -> None:
    assert list(
        discover_sansymphony_pool(
            {
                "Disk_pool_1": SansymphonyPool(
                    name="Disk_pool_1",
                    usage_stats=SimpleUsage(percent_allocated=57.0),
                    status="Running",
                    cache_mode="ReadWrite",
                    pool_type="Dynamic",
                ),
            }
        )
    ) == [Service(item="Disk_pool_1")]


def test_check_sansymphony_pool_item_not_found() -> None:
    section = {
        "Disk_pool_1": SansymphonyPool(
            name="Disk_pool_1",
            usage_stats=SimpleUsage(percent_allocated=57.0),
            status="Running",
            cache_mode="ReadWrite",
            pool_type="Dynamic",
        ),
    }
    assert not list(
        check_sansymphony_pool(
            item="Disk_pool_2",
            params={**FILESYSTEM_DEFAULT_LEVELS},
            section=section,
        )
    )


def test_check_sansymphony_pool_status_running_cache_mode_readwrite() -> None:
    section = {
        "Disk_pool_1": SansymphonyPool(
            name="Disk_pool_1",
            usage_stats=SimpleUsage(percent_allocated=57.0),
            status="Running",
            cache_mode="ReadWrite",
            pool_type="Dynamic",
        ),
    }
    assert list(
        check_sansymphony_pool(
            item="Disk_pool_1",
            params={**FILESYSTEM_DEFAULT_LEVELS},
            section=section,
        )
    ) == [
        Result(
            state=State.OK,
            summary="Dynamic pool Disk_pool_1 is Running, its cache is in ReadWrite mode",
        ),
        Result(state=State.OK, summary="Used: 57.00%"),
        Metric("pool_allocation", 57.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
    ]


def test_check_sansymphony_pool_status_running_cache_mode_read() -> None:
    section = {
        "Disk_pool_1": SansymphonyPool(
            name="Disk_pool_1",
            usage_stats=SimpleUsage(percent_allocated=57.0),
            status="Running",
            cache_mode="Read",  # this is made up
            pool_type="Dynamic",
        ),
    }
    assert list(
        check_sansymphony_pool(
            item="Disk_pool_1",
            params={**FILESYSTEM_DEFAULT_LEVELS},
            section=section,
        )
    ) == [
        Result(
            state=State.WARN,
            summary="Dynamic pool Disk_pool_1 is Running, its cache is in Read mode",
        ),
        Result(state=State.OK, summary="Used: 57.00%"),
        Metric("pool_allocation", 57.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
    ]


def test_check_sansymphony_pool_status_stale() -> None:
    section = {
        "Disk_pool_1": SansymphonyPool(
            name="Disk_pool_1",
            usage_stats=SimpleUsage(percent_allocated=57.0),
            status="Stale",  # this is made up
            cache_mode="ReadWrite",
            pool_type="Dynamic",
        ),
    }
    assert list(
        check_sansymphony_pool(
            item="Disk_pool_1",
            params={**FILESYSTEM_DEFAULT_LEVELS},
            section=section,
        )
    ) == [
        Result(
            state=State.CRIT,
            summary="Dynamic pool Disk_pool_1 is Stale, its cache is in ReadWrite mode",
        ),
        Result(state=State.OK, summary="Used: 57.00%"),
        Metric("pool_allocation", 57.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
    ]


def test_check_sansymphony_pool_percent_allocated() -> None:
    section = {
        "Disk_pool_1": SansymphonyPool(
            name="Disk_pool_1",
            usage_stats=SimpleUsage(percent_allocated=90.0),
            status="Running",
            cache_mode="ReadWrite",
            pool_type="Dynamic",
        ),
    }
    assert list(
        check_sansymphony_pool(
            item="Disk_pool_1",
            params={**FILESYSTEM_DEFAULT_LEVELS},
            section=section,
        )
    ) == [
        Result(
            state=State.OK,
            summary="Dynamic pool Disk_pool_1 is Running, its cache is in ReadWrite mode",
        ),
        Result(state=State.CRIT, summary="Used: 90.00% (warn/crit at 80.00%/90.00%)"),
        Metric("pool_allocation", 90.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
    ]


def test_check_sansymphony_pool_df() -> None:
    section = {
        "Disk_pool_1": SansymphonyPool(
            name="Disk_pool_1",
            usage_stats=Usage(
                allocated_space=Bytes(800),
                available_space=Bytes(200),
                pool_size=Bytes(1000),
            ),
            status="Running",
            cache_mode="ReadWrite",
            pool_type="Dynamic",
        ),
    }
    assert (
        len(
            list(
                check_sansymphony_pool(
                    item="Disk_pool_1",
                    params={
                        **FILESYSTEM_DEFAULT_LEVELS,
                        **MAGIC_FACTOR_DEFAULT_PARAMS,
                    },
                    section=section,
                )
            )
        )
        > 1
    )


def test_check_compatibility_warning() -> None:
    section = {
        "Disk_pool_1": SansymphonyPool(
            name="Disk_pool_1",
            usage_stats=SimpleUsage(percent_allocated=90.0),
            status="Running",
            cache_mode="ReadWrite",
            pool_type="Dynamic",
        ),
    }

    last_check_result = list(
        check_sansymphony_pool(
            item="Disk_pool_1",
            params={
                **FILESYSTEM_DEFAULT_LEVELS,
                **MAGIC_FACTOR_DEFAULT_PARAMS,
                "magic": 0.8,
            },
            section=section,
        )
    )[-1]

    assert isinstance(last_check_result, Result)
    assert last_check_result.state is State.WARN
    assert last_check_result.summary.startswith("Magic factor is not available")
