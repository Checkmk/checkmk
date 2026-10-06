#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.couchbase.agent_based.couchbase_buckets_cache import (
    check_couchbase_buckets_cache,
    discover_couchbase_buckets_cache,
)
from cmk.plugins.couchbase.lib import parse_couchbase_lines

SECTION = parse_couchbase_lines(
    [
        ['{"name": "beer-sample", "ep_cache_miss_rate": 3.5}'],
        ['{"name": "no-cache-data"}'],
    ]
)


def test_discovery_only_yields_buckets_with_cache_miss_rate() -> None:
    assert list(discover_couchbase_buckets_cache(SECTION)) == [Service(item="beer-sample")]


def test_cache_miss_rate_above_upper_levels_is_crit() -> None:
    assert list(
        check_couchbase_buckets_cache("beer-sample", {"cache_misses": (1.0, 2.0)}, SECTION)
    ) == [
        Result(state=State.CRIT, summary="Cache misses: 3.5/s (warn/crit at 1.0/s/2.0/s)"),
        Metric("cache_misses_rate", 3.5, levels=(1.0, 2.0)),
    ]


def test_missing_bucket_yields_nothing() -> None:
    assert not list(check_couchbase_buckets_cache("vanished", {}, SECTION))
