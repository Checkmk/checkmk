#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Service
from cmk.plugins.couchbase.agent_based.couchbase_nodes_cache import (
    check_couchbase_nodes_cache,
    discover_couchbase_nodes_cache,
)
from cmk.plugins.couchbase.lib import parse_couchbase_lines

SECTION = parse_couchbase_lines(
    [
        ['{"name": "node1:8091", "get_hits": 90, "ep_bg_fetched": 10}'],
        ['{"name": "node2:8091", "get_hits": 90}'],
    ]
)


def test_discovery_requires_hits_and_misses() -> None:
    assert list(discover_couchbase_nodes_cache(SECTION)) == [Service(item="node1:8091")]


def test_node_without_misses_yields_nothing() -> None:
    assert not list(check_couchbase_nodes_cache("node2:8091", {}, SECTION))
