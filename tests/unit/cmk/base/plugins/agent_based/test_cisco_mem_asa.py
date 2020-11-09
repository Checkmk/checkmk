#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from cmk.base.plugins.agent_based.cisco_mem_asa import (
    parse_cisco_mem_asa,
    parse_cisco_mem_asa64,
    discovery_cisco_mem,
    _idem_check_cisco_mem,
)

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    Service,
    Result,
    Metric,
    State as state,
)

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import Parameters, ValueStore


@pytest.mark.parametrize("string_table,expected_parsed_data", [
    (
        [[['System memory', '319075344', '754665920', '731194056']],
         [['MEMPOOL_DMA', '41493248', '11754752', '11743928']]],
        {
            "System memory": ['319075344', '754665920', '731194056'],
            "MEMPOOL_DMA": ['41493248', '11754752', '11743928'],
        },
    ),
])
def test_parse_cisco_mem_asa(string_table, expected_parsed_data):
    assert parse_cisco_mem_asa(string_table) == expected_parsed_data


@pytest.mark.parametrize("string_table,expected_parsed_data", [
    (
        [[['System memory', '1251166290', '3043801006'], ['MEMPOOL_DMA', '0', '0'],
          ['MEMPOOL_GLOBAL_SHARED', '0', '0']]],
        {
            "System memory": ['1251166290', '3043801006'],
            "MEMPOOL_DMA": ['0', '0'],
            "MEMPOOL_GLOBAL_SHARED": ['0', '0'],
        },
    ),
])
def test_parse_cisco_mem_asa64(string_table, expected_parsed_data):
    assert parse_cisco_mem_asa64(string_table) == expected_parsed_data


@pytest.mark.parametrize("string_table,expected_parsed_data", [
    ({
        "System memory": ['1251166290', '3043801006'],
        "MEMPOOL_DMA": ['0', '0'],
        "MEMPOOL_GLOBAL_SHARED": ['0', '0'],
    }, [
        "System memory",
        "MEMPOOL_DMA",
        "MEMPOOL_GLOBAL_SHARED",
    ]),
])
def test_discovery_cisco_mem(string_table, expected_parsed_data):
    assert (list(discovery_cisco_mem(string_table)) == list(
        Service(item=item) for item in expected_parsed_data))


@pytest.mark.parametrize("check_args,expected_result", [
    (
        {
            "item": "MEMPOOL_DMA",
            "params": Parameters({
                'trend_perfdata': True,
                'trend_range': 24,
                'trend_showtimeleft': True,
                'trend_timeleft': (12, 6)
            }),
            "section": {
                'System memory': ['3848263744', '8765044672'],
                'MEMPOOL_MSGLYR': ['123040', '8265568'],
                'MEMPOOL_DMA': ['429262192', '378092176'],
                'MEMPOOL_GLOBAL_SHARED': ['1092814800', '95541296'],
            }
        },
        (
            Result(state=state.OK, summary='Usage: 53.2% - 409 MiB of 770 MiB'),
            Metric('mem_used_percent', 53.16899356888102, boundaries=(0.0, None)),
        ),
    ),
])
def test_check_cisco_mem(check_args, expected_result):
    vs: ValueStore = {}
    assert list(_idem_check_cisco_mem(value_store=vs, **check_args)) == list(expected_result)


if __name__ == "__main__":
    pytest.main(["-vvsx", "-T", "unit", __file__])
