#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.elasticsearch.agent_based.elasticsearch_nodes import (
    check_elasticsearch_nodes,
    discover_elasticsearch_nodes,
    parse_elasticsearch_nodes,
)

_STRING_TABLE: list[list[str]] = [
    ["DGfRL2s", "open_file_descriptors", "462"],
    ["DGfRL2s", "max_file_descriptors", "4096"],
    ["DGfRL2s", "cpu_percent", "0"],
    ["DGfRL2s", "cpu_total_in_millis", "157950"],
    ["DGfRL2s", "mem_total_virtual_in_bytes", "7135776768"],
    ["fKw8YbK", "open_file_descriptors", "442"],
    ["fKw8YbK", "max_file_descriptors", "4096"],
    ["fKw8YbK", "cpu_percent", "0"],
    ["fKw8YbK", "cpu_total_in_millis", "94820"],
    ["fKw8YbK", "mem_total_virtual_in_bytes", "7106904064"],
    ["ZwGy2o7", "open_file_descriptors", "453"],
    ["ZwGy2o7", "max_file_descriptors", "4096"],
    ["ZwGy2o7", "cpu_percent", "0"],
    ["ZwGy2o7", "cpu_total_in_millis", "97700"],
    ["ZwGy2o7", "mem_total_virtual_in_bytes", "7123750912"],
    ["huh3AiI", "open_file_descriptors", "453"],
    ["huh3AiI", "max_file_descriptors", "4096"],
    ["huh3AiI", "cpu_percent", "0"],
    ["huh3AiI", "cpu_total_in_millis", "96740"],
    ["huh3AiI", "mem_total_virtual_in_bytes", "7106514944"],
    ["g8YT0-P", "open_file_descriptors", "447"],
    ["g8YT0-P", "max_file_descriptors", "4096"],
    ["g8YT0-P", "cpu_percent", "0"],
    ["g8YT0-P", "cpu_total_in_millis", "104530"],
    ["g8YT0-P", "mem_total_virtual_in_bytes", "7122513920"],
]


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            _STRING_TABLE,
            [
                Service(item="DGfRL2s"),
                Service(item="ZwGy2o7"),
                Service(item="fKw8YbK"),
                Service(item="g8YT0-P"),
                Service(item="huh3AiI"),
            ],
        ),
    ],
)
def test_discover_elasticsearch_nodes(
    string_table: StringTable, expected_discoveries: Sequence[Service]
) -> None:
    parsed = parse_elasticsearch_nodes(string_table)
    result = list(discover_elasticsearch_nodes(parsed))
    assert sorted(result, key=lambda s: s.item or "") == sorted(
        expected_discoveries, key=lambda s: s.item or ""
    )


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "DGfRL2s",
            {"cpu_levels": (75.0, 90.0)},
            _STRING_TABLE,
            [
                Result(state=State.OK, summary="CPU used: 0%"),
                Metric("cpu_percent", 0.0, levels=(75.0, 90.0)),
                Result(state=State.OK, summary="CPU total in ms: 157950"),
                Metric("cpu_total_in_millis", 157950.0),
                Result(state=State.OK, summary="Total virtual memory: 6.65 GiB"),
                Metric("mem_total_virtual_in_bytes", 7135776768.0),
                Result(state=State.OK, summary="Open file descriptors: 462"),
                Metric("open_file_descriptors", 462.0),
                Result(state=State.OK, summary="Max file descriptors: 4096"),
                Metric("max_file_descriptors", 4096.0),
            ],
        ),
        (
            "ZwGy2o7",
            {"cpu_levels": (75.0, 90.0)},
            _STRING_TABLE,
            [
                Result(state=State.OK, summary="CPU used: 0%"),
                Metric("cpu_percent", 0.0, levels=(75.0, 90.0)),
                Result(state=State.OK, summary="CPU total in ms: 97700"),
                Metric("cpu_total_in_millis", 97700.0),
                Result(state=State.OK, summary="Total virtual memory: 6.63 GiB"),
                Metric("mem_total_virtual_in_bytes", 7123750912.0),
                Result(state=State.OK, summary="Open file descriptors: 453"),
                Metric("open_file_descriptors", 453.0),
                Result(state=State.OK, summary="Max file descriptors: 4096"),
                Metric("max_file_descriptors", 4096.0),
            ],
        ),
        (
            "fKw8YbK",
            {"cpu_levels": (75.0, 90.0)},
            _STRING_TABLE,
            [
                Result(state=State.OK, summary="CPU used: 0%"),
                Metric("cpu_percent", 0.0, levels=(75.0, 90.0)),
                Result(state=State.OK, summary="CPU total in ms: 94820"),
                Metric("cpu_total_in_millis", 94820.0),
                Result(state=State.OK, summary="Total virtual memory: 6.62 GiB"),
                Metric("mem_total_virtual_in_bytes", 7106904064.0),
                Result(state=State.OK, summary="Open file descriptors: 442"),
                Metric("open_file_descriptors", 442.0),
                Result(state=State.OK, summary="Max file descriptors: 4096"),
                Metric("max_file_descriptors", 4096.0),
            ],
        ),
        (
            "g8YT0-P",
            {"cpu_levels": (75.0, 90.0)},
            _STRING_TABLE,
            [
                Result(state=State.OK, summary="CPU used: 0%"),
                Metric("cpu_percent", 0.0, levels=(75.0, 90.0)),
                Result(state=State.OK, summary="CPU total in ms: 104530"),
                Metric("cpu_total_in_millis", 104530.0),
                Result(state=State.OK, summary="Total virtual memory: 6.63 GiB"),
                Metric("mem_total_virtual_in_bytes", 7122513920.0),
                Result(state=State.OK, summary="Open file descriptors: 447"),
                Metric("open_file_descriptors", 447.0),
                Result(state=State.OK, summary="Max file descriptors: 4096"),
                Metric("max_file_descriptors", 4096.0),
            ],
        ),
        (
            "huh3AiI",
            {"cpu_levels": (75.0, 90.0)},
            _STRING_TABLE,
            [
                Result(state=State.OK, summary="CPU used: 0%"),
                Metric("cpu_percent", 0.0, levels=(75.0, 90.0)),
                Result(state=State.OK, summary="CPU total in ms: 96740"),
                Metric("cpu_total_in_millis", 96740.0),
                Result(state=State.OK, summary="Total virtual memory: 6.62 GiB"),
                Metric("mem_total_virtual_in_bytes", 7106514944.0),
                Result(state=State.OK, summary="Open file descriptors: 453"),
                Metric("open_file_descriptors", 453.0),
                Result(state=State.OK, summary="Max file descriptors: 4096"),
                Metric("max_file_descriptors", 4096.0),
            ],
        ),
    ],
)
def test_check_elasticsearch_nodes(  # type: ignore[misc]
    item: str,
    params: Mapping[str, Any],
    string_table: StringTable,
    expected_results: Sequence[Result | Metric],
) -> None:
    parsed = parse_elasticsearch_nodes(string_table)
    result = list(check_elasticsearch_nodes(item, params, parsed))
    assert result == expected_results
