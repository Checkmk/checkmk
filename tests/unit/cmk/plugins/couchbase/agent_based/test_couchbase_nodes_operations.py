#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.couchbase.agent_based.couchbase_nodes_operations import (
    check_couchbase_nodes_operations,
    check_couchbase_nodes_operations_total,
    discover_couchbase_nodes_operations,
    discover_couchbase_nodes_operations_total,
    parse_couchbase_nodes_operations,
)

SECTION = parse_couchbase_nodes_operations(
    [
        ["1.5", "node1:8091"],
        ["2.5", "node", "with", "spaces"],
        ["not-a-number", "node3:8091"],
        ["too-short"],
    ]
)


def test_parsing_skips_invalid_lines_and_sums_up_total() -> None:
    assert SECTION == {"node1:8091": 1.5, "node with spaces": 2.5, None: 4.0}


def test_discovery_yields_one_service_per_node() -> None:
    assert list(discover_couchbase_nodes_operations(SECTION)) == [
        Service(item="node1:8091"),
        Service(item="node with spaces"),
    ]


def test_total_service_is_discovered() -> None:
    assert list(discover_couchbase_nodes_operations_total(SECTION)) == [Service()]


def test_node_operations_are_checked_against_upper_levels() -> None:
    assert list(check_couchbase_nodes_operations("node1:8091", {"ops": (1.0, 2.0)}, SECTION)) == [
        Result(state=State.WARN, summary="1.50/s (warn/crit at 1.00/s/2.00/s)"),
        Metric("op_s", 1.5, levels=(1.0, 2.0)),
    ]


def test_total_operations_are_reported() -> None:
    assert list(check_couchbase_nodes_operations_total({}, SECTION)) == [
        Result(state=State.OK, summary="4.00/s"),
        Metric("op_s", 4.0),
    ]


def test_zero_operations_are_still_reported() -> None:
    section = parse_couchbase_nodes_operations([["0", "idle"]])

    assert list(check_couchbase_nodes_operations("idle", {}, section)) == [
        Result(state=State.OK, summary="0.00/s"),
        Metric("op_s", 0.0),
    ]


def test_unknown_node_yields_nothing() -> None:
    assert not list(check_couchbase_nodes_operations("vanished", {}, SECTION))
