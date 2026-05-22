#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.graylog.agent_based.graylog_jvm import check_graylog_jvm, discover_graylog_jvm
from cmk.plugins.graylog.lib import deserialize_and_merge_json

_SECTION = [
    [
        '{"jvm.memory.heap.init": 1073741824, "jvm.memory.heap.used": 461934992, "jvm.memory.heap.max": 1020067840, "jvm.memory.heap.committed": 1020067840, "jvm.memory.heap.usage": 0.45284732435050595}'
    ]
]


def test_discover_graylog_jvm() -> None:
    parsed = deserialize_and_merge_json(_SECTION)
    assert list(discover_graylog_jvm(parsed)) == [Service()]


def test_check_graylog_jvm() -> None:
    parsed = deserialize_and_merge_json(_SECTION)
    assert list(check_graylog_jvm({}, parsed)) == [
        Result(state=State.OK, summary="Used heap space: 441 MiB"),
        Metric("mem_heap", 461934992),
        Result(state=State.OK, summary="Committed heap space: 973 MiB"),
        Metric("mem_heap_committed", 1020067840),
    ]


def test_check_graylog_jvm_no_data() -> None:
    assert list(check_graylog_jvm({}, {"jvm.memory.other": 1})) == [
        Result(state=State.UNKNOWN, summary="No heap space data available"),
    ]
