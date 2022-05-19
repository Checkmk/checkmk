#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.sansymphony_pool import (
    check_sansymphony_pool,
    discover_sansymphony_pool,
    parse_sansymphony_pool,
    SansymphonyPool,
)


def test_parse_sansymphony_pool_no_agent_output() -> None:
    assert parse_sansymphony_pool([]) == {}


def test_parse_sansymphony_pool() -> None:
    assert parse_sansymphony_pool([["Disk_pool_1", "57", "Running", "ReadWrite", "Dynamic",]]) == {
        "Disk_pool_1": SansymphonyPool(
            name="Disk_pool_1",
            percent_allocated=57.0,
            status="Running",
            cache_mode="ReadWrite",
            pool_type="Dynamic",
        ),
    }


def test_discover_sansymphony_pool_no_agent_output() -> None:
    assert list(discover_sansymphony_pool({})) == []


def test_discover_sansymphony_pool() -> None:
    assert list(
        discover_sansymphony_pool(
            {
                "Disk_pool_1": SansymphonyPool(
                    name="Disk_pool_1",
                    percent_allocated=57.0,
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
            percent_allocated=57.0,
            status="Running",
            cache_mode="ReadWrite",
            pool_type="Dynamic",
        ),
    }
    assert (
        list(
            check_sansymphony_pool(
                item="Disk_pool_2",
                params={"allocated_pools_percentage_upper": (80.0, 90.0)},
                section=section,
            )
        )
        == []
    )


def test_check_sansymphony_pool_status_running_cache_mode_readwrite() -> None:
    section = {
        "Disk_pool_1": SansymphonyPool(
            name="Disk_pool_1",
            percent_allocated=57.0,
            status="Running",
            cache_mode="ReadWrite",
            pool_type="Dynamic",
        ),
    }
    assert list(
        check_sansymphony_pool(
            item="Disk_pool_1",
            params={"allocated_pools_percentage_upper": (80.0, 90.0)},
            section=section,
        )
    ) == [
        Result(
            state=State.OK,
            summary="Dynamic pool Disk_pool_1 is Running, its cache is in ReadWrite mode",
        ),
        Result(state=State.OK, summary="Pool allocation: 57.00%"),
        Metric("pool_allocation", 57.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
    ]


def test_check_sansymphony_pool_status_running_cache_mode_read() -> None:
    section = {
        "Disk_pool_1": SansymphonyPool(
            name="Disk_pool_1",
            percent_allocated=57.0,
            status="Running",
            cache_mode="Read",  # this is made up
            pool_type="Dynamic",
        ),
    }
    assert list(
        check_sansymphony_pool(
            item="Disk_pool_1",
            params={"allocated_pools_percentage_upper": (80.0, 90.0)},
            section=section,
        )
    ) == [
        Result(
            state=State.WARN,
            summary="Dynamic pool Disk_pool_1 is Running, its cache is in Read mode",
        ),
        Result(state=State.OK, summary="Pool allocation: 57.00%"),
        Metric("pool_allocation", 57.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
    ]


def test_check_sansymphony_pool_status_stale() -> None:
    section = {
        "Disk_pool_1": SansymphonyPool(
            name="Disk_pool_1",
            percent_allocated=57.0,
            status="Stale",  # this is made up
            cache_mode="ReadWrite",
            pool_type="Dynamic",
        ),
    }
    assert list(
        check_sansymphony_pool(
            item="Disk_pool_1",
            params={"allocated_pools_percentage_upper": (80.0, 90.0)},
            section=section,
        )
    ) == [
        Result(
            state=State.CRIT,
            summary="Dynamic pool Disk_pool_1 is Stale, its cache is in ReadWrite mode",
        ),
        Result(state=State.OK, summary="Pool allocation: 57.00%"),
        Metric("pool_allocation", 57.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
    ]


def test_check_sansymphony_pool_percent_allocated() -> None:
    section = {
        "Disk_pool_1": SansymphonyPool(
            name="Disk_pool_1",
            percent_allocated=90.0,
            status="Running",
            cache_mode="ReadWrite",
            pool_type="Dynamic",
        ),
    }
    assert list(
        check_sansymphony_pool(
            item="Disk_pool_1",
            params={"allocated_pools_percentage_upper": (80.0, 90.0)},
            section=section,
        )
    ) == [
        Result(
            state=State.OK,
            summary="Dynamic pool Disk_pool_1 is Running, its cache is in ReadWrite mode",
        ),
        Result(state=State.CRIT, summary="Pool allocation: 90.00% (warn/crit at 80.00%/90.00%)"),
        Metric("pool_allocation", 90.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
    ]
