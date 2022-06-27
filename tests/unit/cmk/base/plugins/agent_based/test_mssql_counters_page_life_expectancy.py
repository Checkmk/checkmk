#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.mssql_counters_page_life_expectancy import (
    check_mssql_counters_page_life_expectancy,
    discover_mssql_counters_page_life_expectancy,
)


@pytest.mark.parametrize(
    "section, expected_services",
    [
        (
            {
                ("MSSQL_PLANS:Plan_Cache", "_Total"): {
                    "cache_hit_ratio": 2435,
                    "cache_hit_ratio_base": 4293,
                    "cache_object_counts": 48,
                    "cache_objects_in_use": 0,
                    "cache_pages": 1350,
                },
                ("MSSQL_PLANS:Memory_Node", "000"): {
                    "database_node_memory_(kb)": 8280,
                    "foreign_node_memory_(kb)": 0,
                    "free_node_memory_(kb)": 536,
                    "stolen_node_memory_(kb)": 159312,
                    "target_node_memory_(kb)": 617328,
                    "total_node_memory_(kb)": 168128,
                },
                ("MSSQL_PLAN:Buffer_Manager", "None"): {
                    "background_writer_pages/sec": 0,
                    "buffer_cache_hit_ratio": 156,
                    "buffer_cache_hit_ratio_base": 156,
                    "page_life_expectancy": 341774,
                    "page_lookups/sec": 3417048078,
                    "page_reads/sec": 153102,
                    "page_writes/sec": 781084,
                },
                ("MSSQL_PLAN:Buffer_Node", "000"): {
                    "database_pages": 63082,
                    "local_node_page_lookups/sec": 0,
                    "page_life_expectancy": 341774,
                    "remote_node_page_lookups/sec": 0,
                },
            },
            [
                Service(item="MSSQL_PLAN:Buffer_Manager page_life_expectancy"),
                Service(item="MSSQL_PLAN:Buffer_Node 000 page_life_expectancy"),
            ],
        ),
    ],
)
def test_discover_mssql_counters_page_life_expectancy(section, expected_services) -> None:
    assert list(discover_mssql_counters_page_life_expectancy(section)) == expected_services


@pytest.mark.parametrize(
    "item, params, section, expected_result",
    [
        (
            "MSSQL_PLAN:Buffer_Node 000 page_life_expectancy",
            {
                "mssql_min_page_life_expectancy": (350, 300),
            },
            {
                ("MSSQL_PLANS:Plan_Cache", "_Total"): {
                    "cache_hit_ratio": 2435,
                    "cache_hit_ratio_base": 4293,
                    "cache_object_counts": 48,
                    "cache_objects_in_use": 0,
                    "cache_pages": 1350,
                },
                ("MSSQL_PLANS:Memory_Node", "000"): {
                    "database_node_memory_(kb)": 8280,
                    "foreign_node_memory_(kb)": 0,
                    "free_node_memory_(kb)": 536,
                    "stolen_node_memory_(kb)": 159312,
                    "target_node_memory_(kb)": 617328,
                    "total_node_memory_(kb)": 168128,
                },
                ("MSSQL_PLAN:Buffer_Manager", "None"): {
                    "background_writer_pages/sec": 0,
                    "buffer_cache_hit_ratio": 156,
                    "buffer_cache_hit_ratio_base": 156,
                    "page_life_expectancy": 341774,
                    "page_lookups/sec": 3417048078,
                    "page_reads/sec": 153102,
                    "page_writes/sec": 781084,
                },
            },
            [],
        ),
        (
            "MSSQL_PLAN:Buffer_Node 000 page_life_expectancy",
            {
                "mssql_min_page_life_expectancy": (350, 300),
            },
            {
                ("MSSQL_PLANS:Plan_Cache", "_Total"): {
                    "cache_hit_ratio": 2435,
                    "cache_hit_ratio_base": 4293,
                    "cache_object_counts": 48,
                    "cache_objects_in_use": 0,
                    "cache_pages": 1350,
                },
                ("MSSQL_PLANS:Memory_Node", "000"): {
                    "database_node_memory_(kb)": 8280,
                    "foreign_node_memory_(kb)": 0,
                    "free_node_memory_(kb)": 536,
                    "stolen_node_memory_(kb)": 159312,
                    "target_node_memory_(kb)": 617328,
                    "total_node_memory_(kb)": 168128,
                },
                ("MSSQL_PLAN:Buffer_Manager", "None"): {
                    "background_writer_pages/sec": 0,
                    "buffer_cache_hit_ratio": 156,
                    "buffer_cache_hit_ratio_base": 156,
                    "page_life_expectancy": 341774,
                    "page_lookups/sec": 3417048078,
                    "page_reads/sec": 153102,
                    "page_writes/sec": 781084,
                },
                ("MSSQL_PLAN:Buffer_Node", "000"): {
                    "database_pages": 63082,
                    "local_node_page_lookups/sec": 0,
                    "page_life_expectancy": 541774,
                    "remote_node_page_lookups/sec": 0,
                },
            },
            [
                Result(state=State.OK, summary="6 days 6 hours"),
                Metric("page_life_expectancy", 541774.0),
            ],
        ),
        (
            "MSSQL_PLAN:Buffer_Manager page_life_expectancy",
            {
                "mssql_min_page_life_expectancy": (350, 300),
            },
            {
                ("MSSQL_PLANS:Plan_Cache", "_Total"): {
                    "cache_hit_ratio": 2435,
                    "cache_hit_ratio_base": 4293,
                    "cache_object_counts": 48,
                    "cache_objects_in_use": 0,
                    "cache_pages": 1350,
                },
                ("MSSQL_PLANS:Memory_Node", "000"): {
                    "database_node_memory_(kb)": 8280,
                    "foreign_node_memory_(kb)": 0,
                    "free_node_memory_(kb)": 536,
                    "stolen_node_memory_(kb)": 159312,
                    "target_node_memory_(kb)": 617328,
                    "total_node_memory_(kb)": 168128,
                },
                ("MSSQL_PLAN:Buffer_Manager", "None"): {
                    "background_writer_pages/sec": 0,
                    "buffer_cache_hit_ratio": 156,
                    "buffer_cache_hit_ratio_base": 156,
                    "page_life_expectancy": 341774,
                    "page_lookups/sec": 3417048078,
                    "page_reads/sec": 153102,
                    "page_writes/sec": 781084,
                },
                ("MSSQL_PLAN:Buffer_Node", "000"): {
                    "database_pages": 63082,
                    "local_node_page_lookups/sec": 0,
                    "page_life_expectancy": 541774,
                    "remote_node_page_lookups/sec": 0,
                },
            },
            [
                Result(state=State.OK, summary="3 days 22 hours"),
                Metric("page_life_expectancy", 341774.0),
            ],
        ),
    ],
)
def test_check_mssql_counters_page_life_expectancy(item, params, section, expected_result) -> None:
    assert list(check_mssql_counters_page_life_expectancy(item, params, section)) == expected_result
