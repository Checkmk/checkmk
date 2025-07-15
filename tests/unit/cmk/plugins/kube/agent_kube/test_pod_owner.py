#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.plugins.kube.agent_handlers.common import PodOwner
from cmk.plugins.kube.schemata import api
from tests.unit.cmk.plugins.kube.agent_kube.factory import (
    APIPodFactory,
    ContainerResourcesFactory,
    ContainerSpecFactory,
    PodSpecFactory,
    PodStatusFactory,
)


@pytest.mark.parametrize("pod_number", [0, 10, 20])
def test_pod_owner_pod_resources_returns_all_pods(pod_number: int) -> None:
    pod_owner = PodOwner(pods=APIPodFactory.batch(size=pod_number))
    pod_resources = pod_owner.pod_resources()
    assert sum(len(pods) for _, pods in pod_resources) == pod_number


def test_pod_owner_pod_resources_one_pod_per_phase() -> None:
    # Assemble
    pod_owner = PodOwner(
        pods=[
            APIPodFactory.build(status=PodStatusFactory.build(phase=phase)) for phase in api.Phase
        ],
    )

    # Act
    pod_resources = pod_owner.pod_resources()

    # Assert
    for _phase, pods in pod_resources:
        assert len(pods) == 1


def test_pod_owner_memory_resources() -> None:
    container_resources_requirements = ContainerResourcesFactory.build(
        limits=api.ResourcesRequirements(memory=2.0 * 1024),
        requests=api.ResourcesRequirements(memory=1.0 * 1024),
    )
    container_spec = ContainerSpecFactory.build(resources=container_resources_requirements)
    api_pod = APIPodFactory.build(spec=PodSpecFactory.build(containers=[container_spec]))
    pod_owner = PodOwner(pods=[api_pod])
    memory_resources = pod_owner.memory_resources()
    assert memory_resources.count_total == 1
    assert memory_resources.limit == 2.0 * 1024
    assert memory_resources.request == 1.0 * 1024


def test_pod_owner_cpu_resources() -> None:
    container_resources_requirements = ContainerResourcesFactory.build(
        limits=api.ResourcesRequirements(cpu=2.0),
        requests=api.ResourcesRequirements(cpu=1.0),
    )
    container_spec = ContainerSpecFactory.build(resources=container_resources_requirements)
    api_pod = APIPodFactory.build(spec=PodSpecFactory.build(containers=[container_spec]))
    pod_owner = PodOwner(pods=[api_pod])
    cpu_resources = pod_owner.cpu_resources()
    assert cpu_resources.count_total == 1
    assert cpu_resources.limit == 2.0
