#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from .checktestlib import Check

pytestmark = pytest.mark.checks


def _section() -> Mapping[str | None, Mapping[str, object]]:
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
    discovered = sorted(Check("couchbase_buckets_operations").run_discovery(_section()))
    assert discovered == [("bucket-a", {}), ("bucket-b", {})]


def test_discover_total_yields_only_aggregate() -> None:
    # service_name "Couchbase Bucket Operations" has no %s, so any yielded
    # per-bucket string item trips "unexpected type of item discovered:
    # <class 'str'>" in the discovery-time validator -- this is the
    # customer-visible crash.
    discovered = list(Check("couchbase_buckets_operations_total").run_discovery(_section()))
    assert discovered == [(None, {})]
