#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Sequence

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State
from cmk.base.plugins.agent_based.kube_node_info import check_kube_node_info, NodeInfo
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
            NodeInfo(
                architecture="amd64",
                kernel_version="5.13.0-27-generic",
                os_image="Ubuntu 20.04.2 LTS",
                operating_system="linux",
                container_runtime_version="docker://20.10.8",
                name="minikube",
                creation_timestamp=1600000000.0,
                labels={},
                addresses=[],
                cluster="cluster",
            ),
            [
                Result(state=State.OK, summary="Name: minikube"),
                Result(state=State.OK, summary="Age: 1 second"),
                Result(state=State.OK, summary="OS: Ubuntu 20.04.2 LTS"),
                Result(state=State.OK, summary="Container runtime: docker://20.10.8"),
                Result(state=State.OK, notice="Architecture: amd64"),
                Result(state=State.OK, notice="Kernel version: 5.13.0-27-generic"),
                Result(state=State.OK, notice="OS family: linux"),
            ],
            id="overall look of node with age 1 second",
        ),
    ],
)
def test_check_kube_node_info(
    section: NodeInfo, expected_check_result: Sequence[Result], time
) -> None:
    assert list(check_kube_node_info(section)) == expected_check_result
