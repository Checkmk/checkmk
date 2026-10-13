#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.couchbase.agent_based.couchbase_nodes_stats import (
    check_couchbase_nodes_cpu_util,
    check_couchbase_nodes_mem,
    discover_couchbase_nodes_stats,
)
from cmk.plugins.couchbase.lib import parse_couchbase_lines

_MIB = 1024**2

SECTION = parse_couchbase_lines(
    [
        [
            (
                f'{{"name": "node1:8091", "mem_total": {100 * _MIB}, "mem_free": {40 * _MIB},'
                f' "swap_total": {10 * _MIB}, "swap_used": {_MIB}, "cpu_utilization_rate": "n/a"}}'
            )
        ],
        ['{"name": "node2:8091", "mem_total": 100}'],
    ]
)


def test_every_node_is_discovered() -> None:
    assert list(discover_couchbase_nodes_stats(SECTION)) == [
        Service(item="node1:8091"),
        Service(item="node2:8091"),
    ]


def test_ram_levels_in_percent_and_swap_without_levels() -> None:
    assert list(check_couchbase_nodes_mem("node1:8091", {"levels": (50.0, 80.0)}, SECTION)) == [
        Result(
            state=State.WARN,
            summary="RAM: 60.00% - 60.0 MiB of 100 MiB (warn/crit at 50.00%/80.00% used)",
        ),
        Metric("mem_used", 60 * _MIB, levels=(50 * _MIB, 80 * _MIB), boundaries=(0, 100 * _MIB)),
        Result(state=State.OK, summary="Swap: 10.00% - 1.00 MiB of 10.0 MiB"),
        Metric("swap_used", _MIB, boundaries=(0, 10 * _MIB)),
    ]


def test_incomplete_memory_data_yields_nothing() -> None:
    assert not list(check_couchbase_nodes_mem("node2:8091", {}, SECTION))


def test_invalid_cpu_utilization_yields_nothing() -> None:
    assert not list(check_couchbase_nodes_cpu_util("node1:8091", {}, SECTION))
