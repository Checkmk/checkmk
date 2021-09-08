#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based import fortigate_node_memory as fortigate_memory
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State


@pytest.mark.parametrize(
    "string_table, expected",
    [
        (
            [[["ebnfwa02-1", "21", "1"], ["ebnfwa02-2", "11", "2"]]],
            [Service(item="ebnfwa02-1"), Service(item="ebnfwa02-2")],
        ),
        ([[["ebnfwa02-1", "21", "1"]]], [Service(item="Cluster")]),
    ],
)
def test_fortigate_node_memory_discover(string_table, expected):
    section = fortigate_memory.parse_fortigate_node_memory(string_table)
    services = list(fortigate_memory.discovery_fortigate_node_memory(section))
    assert services == expected


@pytest.mark.parametrize(
    "item, params, data, expected",
    [
        (
            "ebnfwa02",
            {"levels": (70.0, 80.0)},
            [[["ebnfwa02-1", "21", "1"], ["ebnfwa02-2", "11", "2"]]],
            [],
        ),
        (
            "ebnfwa02-1",
            {"levels": (70.0, 80.0)},
            [[["ebnfwa02-1", "21", "1"], ["ebnfwa02-2", "11", "2"]]],
            [
                Result(state=State.OK, summary="Usage: 21.00%"),
                Metric("mem_used_percent", 21, levels=(70.00, 80.00), boundaries=(0.00, 100.00)),
            ],
        ),
        (
            "ebnfwa02-2",
            {"levels": (70.0, 80.0)},
            [[["ebnfwa02-1", "21", "1"], ["ebnfwa02-2", "99", "2"]]],
            [
                Result(state=State.CRIT, summary="Usage: 99.00% (warn/crit at 70.00%/80.00%)"),
                Metric("mem_used_percent", 99, levels=(70.0, 80.0), boundaries=(0.0, 100.0)),
            ],
        ),
    ],
)
def test_fortigate_node_memory_check(item, params, data, expected):
    section = fortigate_memory.parse_fortigate_node_memory(data)
    result = fortigate_memory.check_fortigate_node_memory(item, params, section)
    assert list(result) == expected
