#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.couchbase.agent_based.couchbase_buckets_vbuckets import (
    check_couchbase_buckets_vbuckets,
    check_couchbase_buckets_vbuckets_replica,
    discover_couchbase_buckets_vbuckets,
)
from cmk.plugins.couchbase.lib import parse_couchbase_lines

SECTION = parse_couchbase_lines(
    [
        [
            (
                '{"name": "beer-sample", "vb_active_resident_items_ratio": 40,'
                ' "vb_active_itm_memory": 2048, "vb_pending_num": "3",'
                ' "vb_replica_num": "1024", "vb_replica_itm_memory": 4096}'
            )
        ],
        ['{"name": "no-ratio"}'],
    ]
)


def test_discovery_requires_resident_items_ratio() -> None:
    assert list(discover_couchbase_buckets_vbuckets(SECTION)) == [Service(item="beer-sample")]


def test_resident_items_ratio_has_lower_levels() -> None:
    assert list(
        check_couchbase_buckets_vbuckets(
            "beer-sample", {"resident_items_ratio": (50.0, 30.0)}, SECTION
        )
    ) == [
        Result(
            state=State.WARN,
            summary="Resident items ratio: 40.00% (warn/crit below 50.00%/30.00%)",
        ),
        Metric("resident_items_ratio", 40),
        Result(state=State.OK, summary="Item memory: 2.00 KiB"),
        Metric("item_memory", 2048),
        Result(state=State.OK, summary="Pending vBuckets: 3"),
        Metric("pending_vbuckets", 3),
    ]


def test_replica_reports_number_and_memory() -> None:
    assert list(
        check_couchbase_buckets_vbuckets_replica(
            "beer-sample", {"vb_replica_num": (1000, 2000)}, SECTION
        )
    ) == [
        Result(state=State.WARN, summary="Total number: 1024 (warn/crit at 1000/2000)"),
        Metric("vbuckets", 1024, levels=(1000, 2000)),
        Result(state=State.OK, summary="Item memory: 4.00 KiB"),
        Metric("item_memory", 4096),
    ]


def test_replica_of_missing_bucket_yields_nothing() -> None:
    assert not list(check_couchbase_buckets_vbuckets_replica("vanished", {}, SECTION))
