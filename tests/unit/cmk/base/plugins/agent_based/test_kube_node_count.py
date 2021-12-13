#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.kube_node_count import check, check_default_parameters, NodeCount


def test_check_k8s_node_count_default_params() -> None:
    result = list(check(check_default_parameters, NodeCount(worker=0, control_plane=0)))
    assert result == [
        Result(state=State.OK, summary="Number of worker nodes: 0"),
        Metric("k8s_node_count_worker", 0.0, boundaries=(0.0, None)),
        Result(state=State.OK, summary="Number of control plane nodes: 0"),
        Metric("k8s_node_count_control_plane", 0.0, boundaries=(0.0, None)),
    ]
