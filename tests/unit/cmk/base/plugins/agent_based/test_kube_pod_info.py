#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Tuple

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State
from cmk.base.plugins.agent_based.kube_pod_info import check_kube_pod_info, PodInfo
from cmk.base.plugins.agent_based.utils import kube_info


@pytest.fixture(name="time")
def fixture_time(mocker):
    import time as time_mock

    time_mock.time = mocker.Mock(return_value=1600000001.0)
    mocker.patch.object(kube_info, "time", time_mock)
    return time_mock


@pytest.mark.parametrize(
    "section, expected_check_result",
    [
        pytest.param(
            PodInfo(
                namespace="default",
                name="mypod",
                creation_timestamp=1600000000.0,
                labels={},
                node=None,
                host_network=None,
                dns_policy="Default",
                qos_class="burstable",
                host_ip="192.168.49.2",
                pod_ip="172.17.0.2",
                restart_policy="Always",
                uid="dd1019ca-c429-46af-b6b7-8aad47b6081a",
                cluster="cluster",
            ),
            (
                Result(state=State.OK, summary="Name: mypod"),
                Result(state=State.OK, summary="Node: None"),
                Result(state=State.OK, summary="Namespace: default"),
                Result(state=State.OK, summary="Age: 1 second"),
                Result(state=State.OK, summary="Controlled by: None"),
                Result(state=State.OK, notice="QoS class: burstable"),
                Result(state=State.OK, notice="UID: dd1019ca-c429-46af-b6b7-8aad47b6081a"),
                Result(state=State.OK, notice="Restart policy: Always"),
            ),
            id="overall look of pod with age 1 second",
        ),
    ],
)
def test_check_kube_pod_info(
    section: PodInfo, expected_check_result: Tuple[Result, ...], time
) -> None:
    assert tuple(check_kube_pod_info(section)) == expected_check_result
