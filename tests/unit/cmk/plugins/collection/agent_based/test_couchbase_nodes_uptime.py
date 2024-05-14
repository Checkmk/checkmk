#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.collection.agent_based import couchbase_nodes_uptime as cnu

STRING_TABLE = [
    ["ignore_this_for_shortess"],
    ["invalid number", "ladida"],
    ["123", "Node", "with", "weird", "hostname"],
]


@pytest.fixture(name="section", scope="module")
def _get_section() -> cnu.Section:
    return cnu.parse_couchbase_uptime(STRING_TABLE)


def test_discover(section: cnu.Section) -> None:
    assert list(cnu.discover_couchbase_nodes_uptime(section)) == [
        Service(item="Node with weird hostname"),
    ]


def test_check(section: cnu.Section) -> None:
    r1, _r2, metric = cnu.check_couchbase_nodes_uptime("Node with weird hostname", {}, section)
    assert isinstance(r1, Result)
    assert r1.state == State.OK
    assert r1.summary.startswith("Up since ")
    assert metric == Metric("uptime", 123.0)
