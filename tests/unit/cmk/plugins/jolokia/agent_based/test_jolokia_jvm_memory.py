#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.jolokia.agent_based.jolokia_jvm_memory import (
    check_jolokia_jvm_memory,
    discover_jolokia_jvm_memory,
    parse_jolokia_jvm_memory,
)

_STRING_TABLE: StringTable = [
    [
        "MyInstance",
        "java.lang:type=Memory",
        (
            '{"NonHeapMemoryUsage": {"max": 780140544, "init": 7667712, "used": 110167224,'
            ' "committed": 123207680}, "HeapMemoryUsage": {"max": 536870912, "init": 67108864,'
            ' "used": 78331216, "committed": 122683392}, "ObjectPendingFinalizationCount": 0,'
            ' "ObjectName": {"objectName": "java.lang:type=Memory"}, "Verbose": false}'
        ),
    ],
    [
        "MyInstance",
        "java.lang:name=*,type=MemoryPool",
        (
            '{"java.lang:name=Metaspace,type=MemoryPool": {"Name": "Metaspace",'
            ' "Usage": {"max": -1, "init": 0, "used": 463555784, "committed": 525205504}},'
            ' "java.lang:name=Code Cache,type=MemoryPool": {"Name": "Code Cache",'
            ' "Usage": {"max": 536870912, "init": 33554432, "used": 370254912,'
            ' "committed": 373489664}}}'
        ),
    ],
]

_HEAP = Metric("mem_heap", 78331216.0, boundaries=(None, 536870912.0))
_NONHEAP = Metric("mem_nonheap", 110167224.0, boundaries=(None, 780140544.0))


def test_discover_jolokia_jvm_memory() -> None:
    result = list(discover_jolokia_jvm_memory(parse_jolokia_jvm_memory(_STRING_TABLE)))
    assert result == [Service(item="MyInstance")]


@pytest.mark.parametrize(
    "params, expected_results",
    [
        pytest.param(
            {},
            [
                Result(state=State.OK, summary="Heap: 74.7 MiB"),
                _HEAP,
                Result(state=State.OK, summary="14.59%"),
                Result(state=State.OK, summary="Nonheap: 105 MiB"),
                _NONHEAP,
                Result(state=State.OK, summary="14.12%"),
                Result(state=State.OK, summary="Total: 180 MiB"),
                Result(state=State.OK, summary="14.31%"),
            ],
            id="no params",
        ),
        pytest.param(
            {"perc_total": (13.0, 15.0)},
            [
                Result(state=State.OK, summary="Heap: 74.7 MiB"),
                _HEAP,
                Result(state=State.OK, summary="14.59%"),
                Result(state=State.OK, summary="Nonheap: 105 MiB"),
                _NONHEAP,
                Result(state=State.OK, summary="14.12%"),
                Result(state=State.OK, summary="Total: 180 MiB"),
                Result(state=State.WARN, summary="14.31% (warn/crit at 13.00%/15.00%)"),
            ],
            id="perc_total warn",
        ),
        pytest.param(
            {"abs_heap": (450, 460)},
            [
                Result(state=State.CRIT, summary="Heap: 74.7 MiB (warn/crit at 450 B/460 B)"),
                Metric(
                    "mem_heap", 78331216.0, levels=(450.0, 460.0), boundaries=(None, 536870912.0)
                ),
                Result(state=State.OK, summary="14.59%"),
                Result(state=State.OK, summary="Nonheap: 105 MiB"),
                _NONHEAP,
                Result(state=State.OK, summary="14.12%"),
                Result(state=State.OK, summary="Total: 180 MiB"),
                Result(state=State.OK, summary="14.31%"),
            ],
            id="abs_heap crit",
        ),
    ],
)
def test_check_jolokia_jvm_memory(
    params: Mapping[str, object], expected_results: Sequence[object]
) -> None:
    parsed = parse_jolokia_jvm_memory(_STRING_TABLE)
    assert list(check_jolokia_jvm_memory("MyInstance", params, parsed)) == expected_results
