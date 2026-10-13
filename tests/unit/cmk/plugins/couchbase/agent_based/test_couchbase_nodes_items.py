#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.couchbase.agent_based.couchbase_nodes_items import (
    check_couchbase_nodes_items,
    discover_couchbase_nodes_items,
)
from cmk.plugins.couchbase.lib import parse_couchbase_lines

SECTION = parse_couchbase_lines(
    [
        [
            (
                '{"name": "node1:8091", "curr_items": 100, "vb_active_num_non_resident": 7,'
                ' "curr_items_tot": 200}'
            )
        ],
        ['{"name": "node2:8091"}'],
    ]
)


def test_discovery_requires_current_items() -> None:
    assert list(discover_couchbase_nodes_items(SECTION)) == [Service(item="node1:8091")]


def test_item_counts_are_checked_against_upper_levels() -> None:
    assert list(check_couchbase_nodes_items("node1:8091", {"non_residents": (5, 10)}, SECTION)) == [
        Result(state=State.OK, summary="Items in active vBuckets: 100"),
        Metric("items_active", 100),
        Result(state=State.WARN, summary="Non-resident items: 7 (warn/crit at 5/10)"),
        Metric("items_non_res", 7, levels=(5, 10)),
        Result(state=State.OK, summary="Total items in vBuckets: 200"),
        Metric("items", 200),
    ]


def test_node_without_counters_yields_nothing() -> None:
    assert not list(check_couchbase_nodes_items("node2:8091", {}, SECTION))
