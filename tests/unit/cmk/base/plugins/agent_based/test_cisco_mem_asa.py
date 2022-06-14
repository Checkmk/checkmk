#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service
from cmk.base.plugins.agent_based.agent_based_api.v1 import State as state
from cmk.base.plugins.agent_based.cisco_mem_asa import (
    _idem_check_cisco_mem,
    discovery_cisco_mem,
    parse_cisco_mem_asa,
)


@pytest.mark.parametrize(
    "string_table,expected_parsed_data",
    [
        (
            [
                [["System memory", "319075344", "754665920", "731194056"]],
                [["MEMPOOL_DMA", "41493248", "11754752", "11743928"]],
            ],
            {
                "System memory": ["319075344", "754665920", "731194056"],
                "MEMPOOL_DMA": ["41493248", "11754752", "11743928"],
            },
        ),
        (
            [
                [["System memory", "319075344", "754665920", "731194056"]],
                [[]],
            ],
            {
                "System memory": ["319075344", "754665920", "731194056"],
            },
        ),
        (
            [
                [
                    ["System memory", "1251166290", "3043801006"],
                    ["MEMPOOL_DMA", "0", "0"],
                    ["MEMPOOL_GLOBAL_SHARED", "0", "0"],
                ]
            ],
            {
                "System memory": ["1251166290", "3043801006"],
                "MEMPOOL_DMA": ["0", "0"],
                "MEMPOOL_GLOBAL_SHARED": ["0", "0"],
            },
        ),
    ],
)
def test_parse_cisco_mem_asa(string_table, expected_parsed_data) -> None:
    assert parse_cisco_mem_asa(string_table) == expected_parsed_data


@pytest.mark.parametrize(
    "string_table,expected_parsed_data",
    [
        (
            {
                "System memory": ["1251166290", "3043801006"],
                "MEMPOOL_DMA": ["0", "0"],
                "MEMPOOL_GLOBAL_SHARED": ["0", "0"],
            },
            [
                "System memory",
                "MEMPOOL_DMA",
                "MEMPOOL_GLOBAL_SHARED",
            ],
        ),
    ],
)
def test_discovery_cisco_mem(string_table, expected_parsed_data) -> None:
    assert list(discovery_cisco_mem(string_table)) == list(
        Service(item=item) for item in expected_parsed_data
    )


@pytest.mark.parametrize(
    "check_args,expected_result",
    [
        (
            {
                "item": "MEMPOOL_DMA",
                "params": {
                    "trend_perfdata": True,
                    "trend_range": 24,
                    "trend_showtimeleft": True,
                    "trend_timeleft": (12, 6),
                },
                "section": {
                    "System memory": ["3848263744", "8765044672"],
                    "MEMPOOL_MSGLYR": ["123040", "8265568"],
                    "MEMPOOL_DMA": ["429262192", "378092176"],
                    "MEMPOOL_GLOBAL_SHARED": ["1092814800", "95541296"],
                },
            },
            (
                Result(state=state.OK, summary="Usage: 53.17% - 409 MiB of 770 MiB"),
                Metric("mem_used_percent", 53.16899356888102, boundaries=(0.0, None)),
            ),
        ),
    ],
)
def test_check_cisco_mem(check_args, expected_result) -> None:
    assert list(_idem_check_cisco_mem(value_store={}, **check_args)) == list(expected_result)


if __name__ == "__main__":
    # Please keep these lines - they make TDD easy and have no effect on normal test runs.
    # Just run this file from your IDE and dive into the code.
    import os

    from tests.testlib.utils import cmk_path

    assert not pytest.main(
        [
            "--doctest-modules",
            os.path.join(cmk_path(), "cmk/base/plugins/agent_based/cisco_mem_asa.py"),
        ]
    )
    pytest.main(["-T=unit", "-vvsx", __file__])
