#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import CheckResult, Result, State
from cmk.plugins.collection.agent_based.kube_node_kubelet import check_kube_node_kubelet
from cmk.plugins.kube.schemata.api import HealthZ, NodeConnectionError
from cmk.plugins.kube.schemata.section import KubeletInfo


@pytest.mark.parametrize(
    "section, expected_result",
    [
        pytest.param(
            KubeletInfo(
                version="1.2.3",
                proxy_version="1.2.3",
                health=HealthZ(status_code=200, response="ok"),
            ),
            [
                Result(state=State.OK, summary="Healthy"),
                Result(state=State.OK, summary="Version 1.2.3"),
            ],
            id="status_code_ok",
        ),
        pytest.param(
            KubeletInfo(
                version="1.2.3",
                proxy_version="1.2.3",
                health=HealthZ(status_code=500, response="bad"),
            ),
            [
                Result(state=State.CRIT, summary="Not healthy"),
                Result(
                    state=State.OK,
                    notice="Verbose response:\nbad",
                ),
                Result(state=State.OK, summary="Version 1.2.3"),
            ],
            id="status_code_critical",
        ),
        pytest.param(
            KubeletInfo(
                version="1.2.3",
                proxy_version="1.2.3",
                health=NodeConnectionError(message="MaxRetryError..."),
            ),
            [
                Result(state=State.CRIT, summary="Unresponsive Node"),
                Result(
                    state=State.OK,
                    notice="Verbose response:\nMaxRetryError...",
                ),
                Result(state=State.OK, summary="Version 1.2.3"),
            ],
            id="connection timeout",
        ),
    ],
)
def test_check_kube_node_kubelet(section: KubeletInfo, expected_result: CheckResult) -> None:
    result = list(check_kube_node_kubelet(section))
    assert result == expected_result
