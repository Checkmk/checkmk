#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import CheckResult, Result, State
from cmk.plugins.collection.agent_based.kube_cluster_api_health import check
from cmk.plugins.kube.schemata.api import APIHealth, HealthZ
from cmk.plugins.kube.schemata.section import ClusterDetails


@pytest.mark.parametrize(
    "cluster_details, expected_result",
    [
        pytest.param(
            ClusterDetails(
                api_health=APIHealth(
                    ready=HealthZ(status_code=200, response="ok"),
                    live=HealthZ(status_code=200, response="ok"),
                )
            ),
            [
                Result(state=State.OK, summary="Live"),
                Result(state=State.OK, summary="Ready"),
            ],
            id="everything_ok",
        ),
        pytest.param(
            ClusterDetails(
                api_health=APIHealth(
                    ready=HealthZ(status_code=500, response="nok"),
                    live=HealthZ(status_code=200, response="ok"),
                )
            ),
            [
                Result(state=State.OK, summary="Live"),
                Result(state=State.CRIT, summary="Not ready"),
                Result(state=State.OK, notice="Ready response:\nnok"),
                Result(state=State.OK, summary="See service details for more information"),
            ],
            id="not_ready",
        ),
    ],
)
def test_check_kube_node_count_default_params(
    cluster_details: ClusterDetails, expected_result: CheckResult
) -> None:
    result = list(check(cluster_details))
    assert result == expected_result
