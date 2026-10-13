#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.couchbase.agent_based.couchbase_buckets_fragmentation import (
    check_couchbase_buckets_fragmentation,
    discover_couchbase_buckets_fragmentation,
)
from cmk.plugins.couchbase.lib import parse_couchbase_lines

SECTION = parse_couchbase_lines(
    [
        ['{"name": "both", "couch_docs_fragmentation": 30, "couch_views_fragmentation": 60}'],
        ['{"name": "views-only", "couch_views_fragmentation": 10}'],
    ]
)


def test_discovery_requires_docs_fragmentation() -> None:
    assert list(discover_couchbase_buckets_fragmentation(SECTION)) == [Service(item="both")]


def test_docs_and_views_fragmentation_are_checked_against_their_own_levels() -> None:
    assert list(
        check_couchbase_buckets_fragmentation(
            "both", {"docs": (50.0, 70.0), "views": (50.0, 70.0)}, SECTION
        )
    ) == [
        Result(state=State.OK, summary="Documents fragmentation: 30.00%"),
        Metric("docs_fragmentation", 30, levels=(50.0, 70.0)),
        Result(
            state=State.WARN, summary="Views fragmentation: 60.00% (warn/crit at 50.00%/70.00%)"
        ),
        Metric("views_fragmentation", 60, levels=(50.0, 70.0)),
    ]


def test_missing_docs_fragmentation_only_reports_views() -> None:
    assert list(check_couchbase_buckets_fragmentation("views-only", {}, SECTION)) == [
        Result(state=State.OK, summary="Views fragmentation: 10.00%"),
        Metric("views_fragmentation", 10),
    ]
