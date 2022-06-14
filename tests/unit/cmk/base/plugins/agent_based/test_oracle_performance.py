#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.type_defs import CheckPluginName

import cmk.base.config
import cmk.base.plugin_contexts
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State, TableRow
from cmk.base.plugins.agent_based.oracle_performance import (
    inventory_oracle_performance,
    parse_oracle_performance,
)

_AGENT_OUTPUT_1 = [
    ["TWH", "sys_time_model", "DB CPU", "14826"],
    ["TWH", "sys_time_model", "DB time", "69830"],
    [
        "TWH",
        "buffer_pool_statistics",
        "DEFAULT",
        "63743116",
        "55914822",
        "1059719411",
        "21386319",
        "1506816",
        "0",
        "1631907",
    ],
    [
        "TWH",
        "librarycache",
        "SQL AREA",
        "248642",
        "227658",
        "10643092",
        "10582899",
        "13830",
        "14665",
    ],
    ["TWH", "librarycache", "TABLE/PROCEDURE", "99440", "90692", "467944", "453367", "838", "3"],
]
_AGENT_OUTPUT_2 = [
    ["SGP", "sys_time_model", "DB CPU", "55555899"],
    ["SGP", "sys_time_model", "DB time", "60435096"],
    ["SGP", "SGA_info", "Redo Buffers", "14655488"],
    ["SGP", "SGA_info", "Buffer Cache Size", "3875536896"],
    ["SGP", "SGA_info", "Shared Pool Size", "5385486336"],
    ["SGP", "SGA_info", "Large Pool Size", "33554432"],
    ["SGP", "SGA_info", "Java Pool Size", "67108864"],
    ["SGP", "SGA_info", "Streams Pool Size", "0"],
    ["SGP", "SGA_info", "Granule Size", "16777216"],
    ["SGP", "SGA_info", "Maximum SGA Size", "13119782912"],
    ["SGP", "SGA_info", "Startup overhead in Shared Pool", "218103808"],
    ["SGP", "SGA_info", "Free SGA Memory Available", "3187671040"],
    ["SGP", "librarycache", "JAVA RESOURCE", "2", "0", "2", "0", "0", "0"],
    ["SGP", "librarycache", "JAVA DATA", "18", "5", "676", "663", "0", "0"],
]


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        (_AGENT_OUTPUT_1, [Service(item="TWH")]),
        (_AGENT_OUTPUT_2, [Service(item="SGP")]),
    ],
)
def test_discover_oracle_performance(fix_register, string_table, expected_result) -> None:
    check_plugin = fix_register.check_plugins[CheckPluginName("oracle_performance")]
    section = parse_oracle_performance(string_table)
    assert sorted(check_plugin.discovery_function(section)) == expected_result


@pytest.mark.parametrize(
    "string_table, item, expected_result",
    [
        (
            _AGENT_OUTPUT_1,
            "TWH",
            [
                Result(state=State.OK, summary="DB Time: 0.00 1/s"),
                Metric("oracle_db_time", 0.0),
                Result(state=State.OK, summary="DB CPU: 0.00 1/s"),
                Metric("oracle_db_cpu", 0.0),
                Result(state=State.OK, summary="DB Non-Idle Wait: 0.00 1/s"),
                Metric("oracle_db_wait_time", 0.0),
                Result(state=State.OK, summary="Buffer hit ratio: 98.1%"),
                Metric("oracle_buffer_hit_ratio", 98.096392315184),
                Result(state=State.OK, summary="Library cache hit ratio: 99.3%"),
                Metric("oracle_library_cache_hit_ratio", 99.32706545096245),
                Metric("oracle_buffer_busy_wait", 0.0),
                Metric("oracle_consistent_gets", 0.0),
                Metric("oracle_db_block_change", 0.0),
                Metric("oracle_db_block_gets", 0.0),
                Metric("oracle_free_buffer_wait", 0.0),
                Metric("oracle_physical_reads", 0.0),
                Metric("oracle_physical_writes", 0.0),
                Metric("oracle_pin_hits_sum", 0.0),
                Metric("oracle_pins_sum", 0.0),
            ],
        ),
        (
            _AGENT_OUTPUT_2,
            "SGP",
            [
                Result(state=State.OK, summary="DB Time: 0.00 1/s"),
                Metric("oracle_db_time", 0.0),
                Result(state=State.OK, summary="DB CPU: 0.00 1/s"),
                Metric("oracle_db_cpu", 0.0),
                Result(state=State.OK, summary="DB Non-Idle Wait: 0.00 1/s"),
                Metric("oracle_db_wait_time", 0.0),
                Result(state=State.OK, summary="Maximum SGA Size: 12.22 GB"),
                Result(state=State.OK, summary="Buffer Cache Size: 3.61 GB"),
                Result(state=State.OK, summary="Shared Pool Size: 5.02 GB"),
                Result(state=State.OK, summary="Redo Buffers: 13.98 MB"),
                Result(state=State.OK, summary="Java Pool Size: 64.00 MB"),
                Result(state=State.OK, summary="Large Pool Size: 32.00 MB"),
                Result(state=State.OK, summary="Streams Pool Size: 0.00 B"),
                Result(state=State.OK, summary="Library cache hit ratio: 97.8%"),
                Metric("oracle_library_cache_hit_ratio", 97.78761061946902),
                Metric("oracle_pin_hits_sum", 0.0),
                Metric("oracle_pins_sum", 0.0),
                Metric("oracle_sga_buffer_cache", 3875536896.0),
                Metric("oracle_sga_java_pool", 67108864.0),
                Metric("oracle_sga_large_pool", 33554432.0),
                Metric("oracle_sga_redo_buffer", 14655488.0),
                Metric("oracle_sga_shared_pool", 5385486336.0),
                Metric("oracle_sga_size", 13119782912.0),
                Metric("oracle_sga_streams_pool", 0.0),
            ],
        ),
    ],
)
def test_check_oracle_performance(
    monkeypatch, fix_register, string_table, item, expected_result
) -> None:
    # TODO hack: clean this up as soon as the check is migrated
    monkeypatch.setattr(cmk.base.plugin_contexts, "_hostname", "foo")
    monkeypatch.setattr(cmk.base.config.ConfigCache, "host_extra_conf_merged", lambda s, h, r: {})
    monkeypatch.setattr(cmk.base.item_state, "raise_counter_wrap", lambda: None)

    check_plugin = fix_register.check_plugins[CheckPluginName("oracle_performance")]
    section = parse_oracle_performance(string_table)
    assert (
        list(check_plugin.check_function(item=item, params={}, section=section)) == expected_result
    )


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        ([], []),
        (
            _AGENT_OUTPUT_1,
            [],
        ),
        (
            _AGENT_OUTPUT_2,
            [
                TableRow(
                    path=["software", "applications", "oracle", "sga"],
                    key_columns={
                        "sid": "SGP",
                    },
                    inventory_columns={},
                    status_columns={
                        "fixed_size": None,
                        "max_size": 13119782912,
                        "redo_buffer": 14655488,
                        "buf_cache_size": 3875536896,
                        "in_mem_area_size": None,
                        "shared_pool_size": 5385486336,
                        "large_pool_size": 33554432,
                        "java_pool_size": 67108864,
                        "streams_pool_size": 0,
                        "shared_io_pool_size": None,
                        "data_trans_cache_size": None,
                        "granule_size": 16777216,
                        "start_oh_shared_pool": 218103808,
                        "free_mem_avail": 3187671040,
                    },
                ),
            ],
        ),
    ],
)
def test_inventory_oracle_performance(string_table, expected_result) -> None:
    assert (
        list(inventory_oracle_performance(parse_oracle_performance(string_table)))
        == expected_result
    )
