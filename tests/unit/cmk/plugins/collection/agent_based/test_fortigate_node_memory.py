#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State, StringTable
from cmk.plugins.collection.agent_based import fortigate_node_memory as fortigate_memory


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
def test_fortigate_node_memory_discover(
    string_table: Sequence[StringTable], expected: Sequence[Service]
) -> None:
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
def test_fortigate_node_memory_check(
    item: str, params: Mapping[str, object], data: Sequence[StringTable], expected: CheckResult
) -> None:
    section = fortigate_memory.parse_fortigate_node_memory(data)
    result = fortigate_memory.check_fortigate_node_memory(item, params, section)
    assert list(result) == expected
