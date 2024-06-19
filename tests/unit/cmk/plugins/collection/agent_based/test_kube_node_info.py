#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disallow_untyped_defs

from collections.abc import Sequence

import pytest
import pytest_mock

from cmk.agent_based.v2 import Result, State
from cmk.plugins.collection.agent_based.kube_node_info import check_kube_node_info
from cmk.plugins.kube.schemata.api import NodeName, Timestamp
from cmk.plugins.kube.schemata.section import FilteredAnnotations, NodeInfo


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
                name=NodeName("minikube"),
                creation_timestamp=Timestamp(1600000000.0),
                labels={},
                annotations=FilteredAnnotations({}),
                addresses=[],
                cluster="cluster",
                kubernetes_cluster_hostname="host",
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
    section: NodeInfo, expected_check_result: Sequence[Result], mocker: pytest_mock.MockerFixture
) -> None:
    assert list(check_kube_node_info(1600000001.0, section)) == expected_check_result
