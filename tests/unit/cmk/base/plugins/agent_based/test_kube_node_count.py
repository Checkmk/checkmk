#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.kube_node_count import (
    check,
    check_default_parameters,
    NodeCount,
    ReadyCount,
)


def test_check_kube_node_count_default_params() -> None:
    result = list(
        check(
            check_default_parameters,
            NodeCount(
                worker=ReadyCount(ready=0, not_ready=0),
                control_plane=ReadyCount(ready=0, not_ready=1),
            ),
        )
    )
    assert result == [
        Result(state=State.OK, summary="Worker nodes 0/0"),
        Metric("kube_node_count_worker_ready", 0.0, boundaries=(0.0, None)),
        Metric("kube_node_count_worker_not_ready", 0.0),
        Metric("kube_node_count_worker_total", 0.0),
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
        check(
            check_default_parameters,
            NodeCount(
                worker=ReadyCount(ready=10, not_ready=2),
                control_plane=ReadyCount(ready=0, not_ready=0),
            ),
        )
    )
    assert result == [
        Result(state=State.OK, summary="Worker nodes 10/12"),
        Metric("kube_node_count_worker_ready", 10.0, boundaries=(0.0, None)),
        Metric("kube_node_count_worker_not_ready", 2.0),
        Metric("kube_node_count_worker_total", 12.0),
        Result(state=State.OK, summary="No control plane nodes found"),
    ]


def test_check_kube_node_count_params() -> None:
    result = list(
        check(
            {"worker_levels_lower": ("levels", (80, 100))},
            NodeCount(
                worker=ReadyCount(ready=10, not_ready=2),
                control_plane=ReadyCount(ready=0, not_ready=0),
            ),
        )
    )
    assert result == [
        Result(state=State.CRIT, summary="Worker nodes 10/12 (warn/crit below 80/100)"),
        Metric("kube_node_count_worker_ready", 10.0, boundaries=(0.0, None)),
        Metric("kube_node_count_worker_not_ready", 2.0),
        Metric("kube_node_count_worker_total", 12.0),
        Result(state=State.OK, summary="No control plane nodes found"),
    ]
