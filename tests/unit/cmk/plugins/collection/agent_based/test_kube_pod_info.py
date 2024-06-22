#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disallow_untyped_defs


import pytest

from cmk.agent_based.v2 import Result, State
from cmk.plugins.collection.agent_based.kube_pod_info import check_kube_pod_info
from cmk.plugins.kube.schemata.api import IpAddress, NamespaceName, PodUID, Timestamp
from cmk.plugins.kube.schemata.section import FilteredAnnotations, PodInfo


@pytest.mark.parametrize(
    "section, expected_check_result",
    [
        pytest.param(
            PodInfo(
                namespace=NamespaceName("default"),
                name="mypod",
                creation_timestamp=Timestamp(1600000000.0),
                labels={},
                annotations=FilteredAnnotations({}),
                node=None,
                host_network=None,
                dns_policy="Default",
                qos_class="burstable",
                host_ip=IpAddress("192.168.49.2"),
                pod_ip=IpAddress("172.17.0.2"),
                restart_policy="Always",
                uid=PodUID("dd1019ca-c429-46af-b6b7-8aad47b6081a"),
                cluster="cluster",
                kubernetes_cluster_hostname="host",
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
def test_check_kube_pod_info(section: PodInfo, expected_check_result: tuple[Result, ...]) -> None:
    assert tuple(check_kube_pod_info(1600000001.0, section)) == expected_check_result
