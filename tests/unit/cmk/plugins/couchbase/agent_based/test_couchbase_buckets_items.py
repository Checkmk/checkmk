#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.couchbase.agent_based.couchbase_buckets_items import (
    check_couchbase_buckets_items,
    discover_couchbase_buckets_items,
)
from cmk.plugins.couchbase.lib import parse_couchbase_lines

SECTION = parse_couchbase_lines(
    [
        [
            (
                '{"name": "beer-sample", "curr_items_tot": "7303", "disk_write_queue": "12",'
                ' "ep_bg_fetched": "4", "ep_diskqueue_fill": 1.5, "ep_diskqueue_drain": 2.25}'
            )
        ],
        ['{"name": "empty"}'],
    ]
)


def test_discovery_requires_total_items() -> None:
    assert list(discover_couchbase_buckets_items(SECTION)) == [Service(item="beer-sample")]


def test_all_item_counters_are_reported() -> None:
    assert list(
        check_couchbase_buckets_items("beer-sample", {"disk_write_ql": (10, 20)}, SECTION)
    ) == [
        Result(state=State.OK, summary="Total items in vBuckets: 7303"),
        Metric("items_count", 7303),
        Result(state=State.WARN, summary="Items in disk write queue: 12 (warn/crit at 10/20)"),
        Metric("disk_write_ql", 12, levels=(10, 20)),
        Result(state=State.OK, summary="Items fetched from disk: 4"),
        Metric("fetched_items", 4),
        Result(state=State.OK, summary="Disk queue fill rate: 1.50/s"),
        Metric("disk_fill_rate", 1.5),
        Result(state=State.OK, summary="Disk queue drain rate: 2.25/s"),
        Metric("disk_drain_rate", 2.25),
    ]


def test_bucket_without_counters_yields_nothing() -> None:
    assert not list(check_couchbase_buckets_items("empty", {}, SECTION))
