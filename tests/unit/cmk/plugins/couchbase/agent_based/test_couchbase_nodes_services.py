#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.couchbase.agent_based.couchbase_nodes_services import (
    check_couchbase_nodes_services,
    discover_couchbase_nodes_services,
)
from cmk.plugins.couchbase.lib import parse_couchbase_lines

SECTION = parse_couchbase_lines([['{"name": "node1:8091", "services": ["kv", "n1ql", "index"]}']])


def test_discovery_remembers_present_services() -> None:
    assert list(discover_couchbase_nodes_services(SECTION)) == [
        Service(item="node1:8091", parameters={"discovered_services": ["kv", "n1ql", "index"]}),
    ]


def test_unchanged_services_are_ok() -> None:
    assert list(
        check_couchbase_nodes_services(
            "node1:8091", {"discovered_services": ["index", "kv", "n1ql"]}, SECTION
        )
    ) == [Result(state=State.OK, summary="3 services unchanged: index, kv, n1ql")]


def test_vanished_and_appeared_services_are_crit() -> None:
    assert list(
        check_couchbase_nodes_services(
            "node1:8091", {"discovered_services": ["kv", "fts", "eventing"]}, SECTION
        )
    ) == [
        Result(state=State.CRIT, summary="2 services vanished: eventing, fts"),
        Result(state=State.CRIT, summary="2 services appeared: index, n1ql"),
        Result(state=State.OK, summary="1 services unchanged: kv"),
    ]
