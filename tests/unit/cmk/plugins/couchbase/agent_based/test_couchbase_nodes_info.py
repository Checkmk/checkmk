#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.couchbase.agent_based.couchbase_nodes_info import (
    check_couchbase_nodes_status,
    discover_couchbase_nodes_info,
)
from cmk.plugins.couchbase.lib import parse_couchbase_lines

SECTION = parse_couchbase_lines(
    [
        [
            (
                '{"name": "node1:8091", "status": "healthy", "otpNode": "ns_1@10.0.0.1",'
                ' "recoveryType": "none", "version": "7.1.0", "clusterCompatibility": 458753,'
                ' "clusterMembership": "active"}'
            )
        ],
        ['{"name": "node2:8091"}'],
    ]
)


def test_every_node_is_discovered() -> None:
    assert list(discover_couchbase_nodes_info(SECTION)) == [
        Service(item="node1:8091"),
        Service(item="node2:8091"),
    ]


def test_healthy_active_node_is_ok() -> None:
    assert list(check_couchbase_nodes_status("node1:8091", {}, SECTION)) == [
        Result(state=State.OK, summary="Health: healthy"),
        Result(state=State.OK, summary="One-time-password node: ns_1@10.0.0.1"),
        Result(state=State.OK, summary="Recovery type: none"),
        Result(state=State.OK, summary="Version: 7.1.0"),
        Result(state=State.OK, summary="Cluster compatibility: 458753"),
        Result(state=State.OK, summary="Cluster membership: active"),
    ]


def test_node_without_details_reports_unknown_values() -> None:
    assert list(check_couchbase_nodes_status("node2:8091", {}, SECTION)) == [
        Result(state=State.OK, summary="One-time-password node: unknown"),
        Result(state=State.OK, summary="Recovery type: unknown"),
        Result(state=State.OK, summary="Version: unknown"),
        Result(state=State.OK, summary="Cluster compatibility: unknown"),
    ]


@pytest.mark.parametrize(
    "health, params, expected",
    [
        pytest.param("warmup", {}, State.OK, id="warmup default"),
        pytest.param("warmup", {"warmup_state": 1}, State.WARN, id="warmup configured"),
        pytest.param("unhealthy", {}, State.CRIT, id="unhealthy default"),
        pytest.param("unhealthy", {"unhealthy_state": 1}, State.WARN, id="unhealthy configured"),
    ],
)
def test_health_state_follows_params(health: str, params: dict[str, int], expected: State) -> None:
    section = parse_couchbase_lines([[f'{{"name": "n", "status": "{health}"}}']])

    assert next(iter(check_couchbase_nodes_status("n", params, section))) == Result(
        state=expected, summary=f"Health: {health}"
    )


@pytest.mark.parametrize(
    "membership, params, expected",
    [
        pytest.param("inactiveAdded", {}, State.WARN, id="inactive added default"),
        pytest.param("inactiveFailed", {}, State.CRIT, id="inactive failed default"),
        pytest.param(
            "inactiveFailed",
            {"inactive_added_state": 0},
            State.OK,
            id="inactive failed uses added param",
        ),
    ],
)
def test_cluster_membership_state_follows_params(
    membership: str, params: dict[str, int], expected: State
) -> None:
    section = parse_couchbase_lines([[f'{{"name": "n", "clusterMembership": "{membership}"}}']])

    assert list(check_couchbase_nodes_status("n", params, section))[-1] == Result(
        state=expected, summary=f"Cluster membership: {membership}"
    )
