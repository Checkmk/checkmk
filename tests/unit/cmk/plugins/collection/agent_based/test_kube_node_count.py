#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import polyfactory.factories.pydantic_factory
import pytest

from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.collection.agent_based.kube_node_count import (
    _check_levels,
    check_default_parameters,
    KubeNodeCountVSResult,
    NodeType,
    ReadyCount,
)
from cmk.plugins.kube.schemata.section import CountableNode, NodeCount


class CountableNodeFactory(polyfactory.factories.pydantic_factory.ModelFactory):
    __model__ = CountableNode


def test_check_levels_default_params_worker() -> None:
    result = list(
        _check_levels(
            ReadyCount(ready=0, not_ready=0, total=0),
            NodeType.worker,
            check_default_parameters,
        )
    )
    assert result == [
        Result(state=State.OK, summary="No worker nodes found"),
        Metric("kube_node_count_worker_ready", 0.0, boundaries=(0.0, None)),
        Metric("kube_node_count_worker_not_ready", 0.0),
        Metric("kube_node_count_worker_total", 0.0),
    ]


def test_check_kube_node_count_default_params_control_plane() -> None:
    result = list(
        _check_levels(
            ReadyCount(ready=0, not_ready=1, total=1),
            NodeType.control_plane,
            check_default_parameters,
        )
    )
    assert result == [
        Result(
            state=State.OK,
            summary="Control plane nodes 0/1",
        ),
        Metric("kube_node_count_control_plane_ready", 0.0, boundaries=(0.0, None)),
        Metric("kube_node_count_control_plane_not_ready", 1.0),
        Metric("kube_node_count_control_plane_total", 1.0),
    ]


def test_check_kube_node_count_default_params_cp_zero() -> None:
    result = list(
        _check_levels(
            ReadyCount(ready=0, not_ready=0, total=0),
            NodeType.control_plane,
            check_default_parameters,
        )
    )
    assert result == [
        Result(state=State.OK, summary="No control plane nodes found"),
        Metric("kube_node_count_control_plane_ready", 0.0, boundaries=(0.0, None)),
        Metric("kube_node_count_control_plane_not_ready", 0.0),
        Metric("kube_node_count_control_plane_total", 0.0),
    ]


def test_check_kube_node_count_params() -> None:
    result = list(
        _check_levels(
            ReadyCount(ready=10, not_ready=2, total=12),
            NodeType.worker,
            KubeNodeCountVSResult(
                control_plane_roles=["master", "control_plane_roles"],
                worker_levels_lower=("levels", (80, 100)),
                worker_levels_upper="no_levels",
                control_plane_levels_lower="no_levels",
                control_plane_levels_upper="no_levels",
            ),
        )
    )
    assert result == [
        Result(state=State.CRIT, summary="Worker nodes 10/12 (warn/crit below 80/100)"),
        Metric("kube_node_count_worker_ready", 10.0, boundaries=(0.0, None)),
        Metric("kube_node_count_worker_not_ready", 2.0),
        Metric("kube_node_count_worker_total", 12.0),
    ]


def test__check_levels_zero_control_plane_nodes_with_levels() -> None:
    results = list(
        _check_levels(
            ReadyCount(ready=0, not_ready=0, total=0),
            NodeType.control_plane,
            KubeNodeCountVSResult(
                control_plane_roles=["master", "control_plane"],
                worker_levels_lower="no_levels",
                worker_levels_upper="no_levels",
                control_plane_levels_lower=("levels", (1, 1)),
                control_plane_levels_upper="no_levels",
            ),
        )
    )
    assert any(isinstance(r, Result) and r.state == State.CRIT for r in results)


@pytest.mark.parametrize("node_count", [0, 10, 20])
def test_node_count_returns_number_of_nodes_ready_not_ready(node_count: int) -> None:
    section = NodeCount(nodes=CountableNodeFactory.batch(size=node_count))
    worker, control_plane = ReadyCount.node_count(["master", "control_plane"], section)
    assert worker.total + control_plane.total == node_count


def test_node_control_plane_count() -> None:
    section = NodeCount(nodes=CountableNodeFactory.batch(size=1, roles=["master"], ready=True))
    worker, control_plane = ReadyCount.node_count(["master", "control_plane"], section)
    assert worker.total == 0
    assert control_plane.total == 1
    assert control_plane.ready == 1


def test_node_control_plane_not_ready_count() -> None:
    section = NodeCount(nodes=CountableNodeFactory.batch(size=1, roles=["master"], ready=False))
    _worker, control_plane = ReadyCount.node_count(["master", "control_plane"], section)
    assert control_plane.not_ready == 1
