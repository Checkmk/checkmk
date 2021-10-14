#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State
from cmk.base.plugins.agent_based.k8s_cluster_api_health import check
from cmk.base.plugins.agent_based.utils.k8s import APIHealth, APIHealthStatus, ClusterInfo


@pytest.mark.parametrize(
    "cluster_details, expected_result",
    [
        pytest.param(
            ClusterInfo(
                api_health=APIHealth(
                    ready=APIHealthStatus(status_code=200, response="ok", verbose_response=None),
                    live=APIHealthStatus(status_code=200, response="ok", verbose_response=None),
                )
            ),
            [
                Result(state=State.OK, summary="Readiness probe ok"),
                Result(state=State.OK, summary="Liveness probe ok"),
            ],
            id="everything_ok",
        ),
        pytest.param(
            ClusterInfo(
                api_health=APIHealth(
                    ready=APIHealthStatus(
                        status_code=500, response="nok", verbose_response="some\nvery\nlong\noutput"
                    ),
                    live=APIHealthStatus(status_code=200, response="ok", verbose_response=None),
                )
            ),
            [
                Result(state=State.OK, notice="some\nvery\nlong\noutput"),
                Result(state=State.CRIT, summary="Readiness probe nok"),
                Result(state=State.OK, summary="Liveness probe ok"),
            ],
            id="not_ready",
        ),
    ],
)
def test_check_k8s_node_count_default_params(cluster_details: ClusterInfo, expected_result) -> None:
    result = list(check(cluster_details))
    assert result == expected_result
