#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.couchbase.agent_based import couchbase_buckets_operations as cbo


def _section() -> cbo.Section:
    # parse_couchbase_buckets_operations keys buckets by name and adds a
    # summed aggregate under the None key. Build the post-parse shape
    # directly so both discovery paths can be exercised deterministically.
    return {
        "bucket-a": {
            "name": "bucket-a",
            "ops": 10.0,
            "cmd_get": 5.0,
            "cmd_set": 2.0,
            "ep_num_ops_del_meta": 0.0,
            "ep_ops_create": 1.0,
            "ep_ops_update": 2.0,
        },
        "bucket-b": {
            "name": "bucket-b",
            "ops": 20.0,
            "cmd_get": 8.0,
            "cmd_set": 4.0,
            "ep_num_ops_del_meta": 0.0,
            "ep_ops_create": 2.0,
            "ep_ops_update": 6.0,
        },
        None: {
            "ops": 30.0,
            "cmd_get": 13.0,
            "cmd_set": 6.0,
            "ep_num_ops_del_meta": 0.0,
            "ep_ops_create": 3.0,
            "ep_ops_update": 8.0,
        },
    }


def test_discover_per_bucket_skips_aggregate() -> None:
    # service_name "Couchbase Bucket %s Operations" requires an item, so a
    # yielded aggregate (item=None) trips "unexpected type of item discovered:
    # <class 'NoneType'>" in the discovery-time validator.
    discovered = sorted(
        cbo.discover_couchbase_buckets_operations(_section()),
        key=lambda service: service.item or "",
    )
    assert discovered == [Service(item="bucket-a"), Service(item="bucket-b")]


def test_discover_total_yields_only_aggregate() -> None:
    # service_name "Couchbase Bucket Operations" has no %s, so any yielded
    # per-bucket string item trips "unexpected type of item discovered:
    # <class 'str'>" in the discovery-time validator -- this is the
    # customer-visible crash.
    discovered = list(cbo.discover_couchbase_buckets_operations_total(_section()))
    assert discovered == [Service()]


_PARSED = cbo.parse_couchbase_buckets_operations(
    [
        [
            (
                '{"name": "beer-sample", "ops": 10.5, "cmd_get": 5.0, "cmd_set": 2.0,'
                ' "ep_ops_create": 1.0, "ep_ops_update": 2.0, "ep_num_ops_del_meta": 0.5}'
            )
        ],
        ['{"name": "travel-sample", "ops": 20.0}'],
    ]
)


def test_parsed_bucket_operations_are_checked_against_upper_levels() -> None:
    assert list(
        cbo.check_couchbase_buckets_operations("beer-sample", {"ops": (10.0, 20.0)}, _PARSED)
    ) == [
        Result(
            state=State.WARN, summary="Total (per server): 10.50/s (warn/crit at 10.00/s/20.00/s)"
        ),
        Metric("op_s", 10.5, levels=(10.0, 20.0)),
        Result(state=State.OK, summary="Gets: 5.00/s"),
        Result(state=State.OK, summary="Sets: 2.00/s"),
        Result(state=State.OK, summary="Creates: 1.00/s"),
        Result(state=State.OK, summary="Updates: 2.00/s"),
        Result(state=State.OK, summary="Deletes: 0.50/s"),
    ]


def test_total_operations_are_checked_like_a_bucket() -> None:
    assert list(cbo.check_couchbase_buckets_operations_total({}, _section())) == [
        Result(state=State.OK, summary="Total (per server): 30.00/s"),
        Metric("op_s", 30.0),
        Result(state=State.OK, summary="Gets: 13.00/s"),
        Result(state=State.OK, summary="Sets: 6.00/s"),
        Result(state=State.OK, summary="Creates: 3.00/s"),
        Result(state=State.OK, summary="Updates: 8.00/s"),
        Result(state=State.OK, summary="Deletes: 0.00/s"),
    ]


def test_unknown_bucket_yields_nothing() -> None:
    assert not list(cbo.check_couchbase_buckets_operations("vanished", {}, _PARSED))
