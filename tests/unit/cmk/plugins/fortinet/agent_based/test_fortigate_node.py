#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.fortinet.agent_based.fortigate_node import (
    check_fortigate_cluster,
    check_fortigate_node_ses,
    ClusterInfo,
    discover_fortigate_cluster,
    discover_fortigate_node_ses,
    Node,
    parse_fortigate_node,
    Section,
)

_STANDALONE = [[["1", "DEPTHA-HA"]], [["", "0", "19", "443", "1"]]]
_CLUSTER = [
    [["3", "DEPTHA-HA"]],
    [["NODE-01", "13", "52", "1884", "1"], ["", "1", "21", "742", "2"]],
]


@pytest.mark.parametrize(
    "string_table, expected",
    [
        pytest.param(
            _STANDALONE,
            Section(
                cluster_info=ClusterInfo(system_mode="1", group_name="DEPTHA-HA"),
                nodes={"Cluster": Node(cpu=0.0, memory=19, sessions=443)},
            ),
            id="single node is named 'Cluster'",
        ),
        pytest.param(
            _CLUSTER,
            Section(
                cluster_info=ClusterInfo(system_mode="3", group_name="DEPTHA-HA"),
                nodes={
                    "NODE-01": Node(cpu=13.0, memory=52, sessions=1884),
                    "Node 2": Node(cpu=1.0, memory=21, sessions=742),
                },
            ),
            id="nameless nodes fall back to their OID end",
        ),
        pytest.param(
            [[], []],
            Section(cluster_info=None, nodes={}),
            id="empty",
        ),
    ],
)
def test_parse_fortigate_node(string_table: Sequence[StringTable], expected: Section) -> None:
    assert parse_fortigate_node(string_table) == expected


def test_discover_fortigate_cluster() -> None:
    assert list(discover_fortigate_cluster(parse_fortigate_node(_CLUSTER))) == [Service()]


def test_discover_fortigate_cluster_without_cluster_info() -> None:
    assert not list(discover_fortigate_cluster(Section(cluster_info=None, nodes={})))


def test_check_fortigate_cluster() -> None:
    assert list(check_fortigate_cluster(parse_fortigate_node(_CLUSTER))) == [
        Result(state=State.OK, summary="System mode: Active/Passive, Group: DEPTHA-HA")
    ]


def test_discover_fortigate_node_sessions() -> None:
    assert list(discover_fortigate_node_ses(parse_fortigate_node(_CLUSTER))) == [
        Service(item="NODE-01"),
        Service(item="Node 2"),
    ]


def test_check_fortigate_node_sessions() -> None:
    assert list(
        check_fortigate_node_ses(
            "NODE-01", {"levels": (1000, 150000)}, parse_fortigate_node(_CLUSTER)
        )
    ) == [
        Result(state=State.WARN, summary="Sessions: 1884 (warn/crit at 1000/150000)"),
        Metric("session", 1884.0, levels=(1000.0, 150000.0)),
    ]


def test_check_fortigate_node_sessions_missing_item() -> None:
    assert not list(
        check_fortigate_node_ses(
            "missing", {"levels": (1000, 2000)}, parse_fortigate_node(_CLUSTER)
        )
    )
