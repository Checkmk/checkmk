#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.couchbase.agent_based.couchbase_buckets_mem import (
    check_couchbase_bucket_mem,
    discover_couchbase_buckets_mem,
)
from cmk.plugins.couchbase.lib import parse_couchbase_lines

_MIB = 1024**2

SECTION = parse_couchbase_lines(
    [
        [
            (
                f'{{"name": "beer-sample", "mem_total": {100 * _MIB}, "mem_free": {20 * _MIB},'
                f' "ep_mem_low_wat": {50 * _MIB}, "ep_mem_high_wat": {90 * _MIB}}}'
            )
        ],
        ['{"name": "no-free", "mem_total": 100}'],
    ]
)


def test_discovery_requires_total_and_free_memory() -> None:
    assert list(discover_couchbase_buckets_mem(SECTION)) == [Service(item="beer-sample")]


def test_percentage_levels_apply_to_used_memory() -> None:
    assert list(check_couchbase_bucket_mem("beer-sample", {"levels": (70.0, 90.0)}, SECTION)) == [
        Result(
            state=State.WARN,
            summary="Usage: 80.00% - 80.0 MiB of 100 MiB (warn/crit at 70.00%/90.00% used)",
        ),
        Metric(
            "memused_couchbase_bucket",
            80 * _MIB,
            levels=(70 * _MIB, 90 * _MIB),
            boundaries=(0, 100 * _MIB),
        ),
        Result(state=State.OK, summary="Low watermark: 50.0 MiB"),
        Metric("mem_low_wat", 50 * _MIB),
        Result(state=State.OK, summary="High watermark: 90.0 MiB"),
        Metric("mem_high_wat", 90 * _MIB),
    ]


def test_absolute_levels_apply_to_used_memory() -> None:
    results = list(
        check_couchbase_bucket_mem("beer-sample", {"levels": (90 * _MIB, 95 * _MIB)}, SECTION)
    )

    assert results[0] == Result(state=State.OK, summary="Usage: 80.00% - 80.0 MiB of 100 MiB")


def test_incomplete_memory_data_skips_usage() -> None:
    assert not list(check_couchbase_bucket_mem("no-free", {"levels": None}, SECTION))
