#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.couchbase.agent_based.couchbase_nodes_size import (
    check_plugin_couchbase_nodes_size_couch_views,
    check_plugin_couchbase_nodes_size_docs,
    check_plugin_couchbase_nodes_size_spacial_views,
    discover_couchbase_nodes_size,
)
from cmk.plugins.couchbase.lib import parse_couchbase_lines

SECTION = parse_couchbase_lines(
    [
        [
            (
                '{"name": "node1:8091",'
                ' "couch_docs_actual_disk_size": 2048, "couch_docs_data_size": 1024,'
                ' "couch_spatial_disk_size": 4096, "couch_spatial_data_size": 3072,'
                ' "couch_views_actual_disk_size": 8192}'
            )
        ]
    ]
)


def test_every_node_is_discovered() -> None:
    assert list(discover_couchbase_nodes_size(SECTION)) == [Service(item="node1:8091")]


def test_documents_size_is_checked_against_upper_levels() -> None:
    assert list(
        check_plugin_couchbase_nodes_size_docs.check_function(
            item="node1:8091", params={"size_on_disk": (1000, 3000)}, section=SECTION
        )
    ) == [
        Result(state=State.WARN, summary="Size on disk: 2.00 KiB (warn/crit at 1000 B/2.93 KiB)"),
        Metric("size_on_disk", 2048, levels=(1000, 3000)),
        Result(state=State.OK, summary="Data size: 1.00 KiB"),
        Metric("data_size", 1024),
    ]


def test_spacial_views_use_spatial_keys() -> None:
    assert list(
        check_plugin_couchbase_nodes_size_spacial_views.check_function(
            item="node1:8091", params={}, section=SECTION
        )
    ) == [
        Result(state=State.OK, summary="Size on disk: 4.00 KiB"),
        Metric("size_on_disk", 4096),
        Result(state=State.OK, summary="Data size: 3.00 KiB"),
        Metric("data_size", 3072),
    ]


def test_missing_data_size_only_reports_disk_size() -> None:
    assert list(
        check_plugin_couchbase_nodes_size_couch_views.check_function(
            item="node1:8091", params={}, section=SECTION
        )
    ) == [
        Result(state=State.OK, summary="Size on disk: 8.00 KiB"),
        Metric("size_on_disk", 8192),
    ]
