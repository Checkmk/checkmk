#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.graylog_jvm import check_graylog_jvm, discover_graylog_jvm
from cmk.plugins.lib.graylog import deserialize_and_merge_json


@pytest.mark.parametrize(
    "info, expected_discoveries",
    [
        (
            [
                [
                    '{"jvm.memory.heap.init": 1073741824, "jvm.memory.heap.used": 461934992, "jvm.memory.heap.max": 1020067840, "jvm.memory.heap.committed": 1020067840, "jvm.memory.heap.usage": 0.45284732435050595}'
                ]
            ],
            [(None, {})],
        ),
    ],
)
def test_discover_graylog_jvm(
    info: StringTable, expected_discoveries: Sequence[tuple[str | None, Mapping[str, Any]]]
) -> None:
    """Test discovery function for graylog_jvm check."""
    parsed = deserialize_and_merge_json(info)
    result = list(discover_graylog_jvm(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, info, expected_results",
    [
        (
            None,
            {},
            [
                [
                    '{"jvm.memory.heap.init": 1073741824, "jvm.memory.heap.used": 461934992, "jvm.memory.heap.max": 1020067840, "jvm.memory.heap.committed": 1020067840, "jvm.memory.heap.usage": 0.45284732435050595}'
                ]
            ],
            [
                (0, "Used heap space: 441 MiB", [("mem_heap", 461934992, None, None)]),
                (
                    0,
                    "Committed heap space: 973 MiB",
                    [("mem_heap_committed", 1020067840, None, None)],
                ),
            ],
        ),
    ],
)
def test_check_graylog_jvm(
    item: str, params: Mapping[str, Any], info: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for graylog_jvm check."""
    parsed = deserialize_and_merge_json(info)
    result = list(check_graylog_jvm(item, params, parsed))
    assert result == expected_results
