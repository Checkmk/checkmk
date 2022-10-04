#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from tests.unit.cmk.special_agents.agent_kube.factory import (
    APIPodFactory,
    ContainerResourcesFactory,
    ContainerSpecFactory,
    PodSpecFactory,
    PodStatusFactory,
)

from cmk.special_agents.agent_kube import PodOwner
from cmk.special_agents.utils_kubernetes.schemata import api, section


@pytest.mark.parametrize("pod_number", [0, 10, 20])
def test_statefulset_pod_resources_returns_all_pods(pod_number: int) -> None:
    statefulset = PodOwner(pods=APIPodFactory.batch(size=pod_number))
    pod_resources = statefulset.pod_resources()
    assert sum(len(pods) for _, pods in pod_resources) == pod_number


def test_statefulset_pod_resources_one_pod_per_phase() -> None:
    statefulset = PodOwner(
        pods=[
            APIPodFactory.build(status=PodStatusFactory.build(phase=phase)) for phase in api.Phase
        ],
    )
    pod_resources = statefulset.pod_resources()
    for _phase, pods in pod_resources:
        assert len(pods) == 1


def test_statefulset_memory_resources() -> None:
    container_resources_requirements = ContainerResourcesFactory.build(
        limits=api.ResourcesRequirements(memory=2.0 * 1024),
        requests=api.ResourcesRequirements(memory=1.0 * 1024),
    )
    container_spec = ContainerSpecFactory.build(resources=container_resources_requirements)
    api_pod = APIPodFactory.build(spec=PodSpecFactory.build(containers=[container_spec]))
    statefulset = PodOwner(pods=[api_pod])
    memory_resources = statefulset.memory_resources()
    assert memory_resources.count_total == 1
    assert memory_resources.limit == 2.0 * 1024
    assert memory_resources.request == 1.0 * 1024


def test_statefulset_cpu_resources() -> None:
    container_resources_requirements = ContainerResourcesFactory.build(
        limits=api.ResourcesRequirements(cpu=2.0),
        requests=api.ResourcesRequirements(cpu=1.0),
    )
    container_spec = ContainerSpecFactory.build(resources=container_resources_requirements)
    api_pod = APIPodFactory.build(spec=PodSpecFactory.build(containers=[container_spec]))
    statefulset = PodOwner(pods=[api_pod])
    cpu_resources = statefulset.cpu_resources()
    assert cpu_resources.count_total == 1
    assert cpu_resources.limit == 2.0
    assert cpu_resources.request == 1.0


@pytest.mark.parametrize("pod_number", [0, 10, 20])
def test_daemon_set_pod_resources_returns_all_pods(pod_number: int) -> None:
    daemon_set = PodOwner(pods=APIPodFactory.batch(size=pod_number))
    resources = dict(daemon_set.pod_resources())
    pod_resources = section.PodResources(**resources)
    assert sum(len(pods) for _, pods in pod_resources) == pod_number


def test_daemon_set_pod_resources_one_pod_per_phase() -> None:
    daemon_set = PodOwner(
        pods=[
            APIPodFactory.build(status=PodStatusFactory.build(phase=phase)) for phase in api.Phase
        ],
    )
    resources = dict(daemon_set.pod_resources())
    pod_resources = section.PodResources(**resources)
    for _phase, pods in pod_resources:
        assert len(pods) == 1


def test_daemonset_memory_resources() -> None:
    container_resources_requirements = ContainerResourcesFactory.build(
        limits=api.ResourcesRequirements(memory=2.0 * 1024),
        requests=api.ResourcesRequirements(memory=1.0 * 1024),
    )
    container_spec = ContainerSpecFactory.build(resources=container_resources_requirements)
    api_pod = APIPodFactory.build(spec=PodSpecFactory.build(containers=[container_spec]))
    daemonset = PodOwner(pods=[api_pod])
    memory_resources = daemonset.memory_resources()
    assert memory_resources.count_total == 1
    assert memory_resources.limit == 2.0 * 1024
    assert memory_resources.request == 1.0 * 1024


def test_daemonset_cpu_resources() -> None:
    container_resources_requirements = ContainerResourcesFactory.build(
        limits=api.ResourcesRequirements(cpu=2.0),
        requests=api.ResourcesRequirements(cpu=1.0),
    )
    container_spec = ContainerSpecFactory.build(resources=container_resources_requirements)
    api_pod = APIPodFactory.build(spec=PodSpecFactory.build(containers=[container_spec]))
    daemonset = PodOwner(pods=[api_pod])
    cpu_resources = daemonset.cpu_resources()
    assert cpu_resources.count_total == 1
    assert cpu_resources.limit == 2.0
    assert cpu_resources.request == 1.0


def test_node_memory_resources() -> None:
    container_resources_requirements = ContainerResourcesFactory.build(
        limits=api.ResourcesRequirements(memory=2.0 * 1024),
        requests=api.ResourcesRequirements(memory=1.0 * 1024),
    )
    container_spec = ContainerSpecFactory.build(resources=container_resources_requirements)
    node = PodOwner(
        pods=[APIPodFactory.build(spec=PodSpecFactory.build(containers=[container_spec]))],
    )
    memory_resources = node.memory_resources()
    assert memory_resources.count_total == 1
    assert memory_resources.limit == 2.0 * 1024
    assert memory_resources.request == 1.0 * 1024


def test_node_cpu_resources() -> None:
    container_resources_requirements = ContainerResourcesFactory.build(
        limits=api.ResourcesRequirements(cpu=2.0),
        requests=api.ResourcesRequirements(cpu=1.0),
    )
    container_spec = ContainerSpecFactory.build(resources=container_resources_requirements)
    node = PodOwner(
        pods=[APIPodFactory.build(spec=PodSpecFactory.build(containers=[container_spec]))],
    )
    cpu_resources = node.cpu_resources()
    assert cpu_resources.count_total == 1
    assert cpu_resources.limit == 2.0
    assert cpu_resources.request == 1.0


@pytest.mark.parametrize("node_pods", [0, 10, 20])
def test_node_pod_resources_returns_all_node_pods(node_pods: int) -> None:
    node = PodOwner(
        pods=APIPodFactory.batch(size=node_pods),
    )
    resources = dict(node.pod_resources())
    pod_resources = section.PodResources(**resources)
    assert sum(len(pods) for _, pods in pod_resources) == node_pods


def test_node_pod_resources_one_pod_per_phase() -> None:
    node = PodOwner(
        pods=[
            APIPodFactory.build(status=PodStatusFactory.build(phase=phase)) for phase in api.Phase
        ],
    )
    resources = dict(node.pod_resources())
    pod_resources = section.PodResources(**resources)
    for _phase, pods in pod_resources:
        assert len(pods) == 1


def test_deployment_memory_resources() -> None:
    container_resources_requirements = ContainerResourcesFactory.build(
        limits=api.ResourcesRequirements(memory=2.0 * 1024),
        requests=api.ResourcesRequirements(memory=1.0 * 1024),
    )
    container_spec = ContainerSpecFactory.build(resources=container_resources_requirements)
    api_pod = APIPodFactory.build(spec=PodSpecFactory.build(containers=[container_spec]))
    deployment = PodOwner(pods=[api_pod])
    memory_resources = deployment.memory_resources()
    assert memory_resources.count_total == 1
    assert memory_resources.limit == 2.0 * 1024
    assert memory_resources.request == 1.0 * 1024


def test_deployment_cpu_resources() -> None:
    container_resources_requirements = ContainerResourcesFactory.build(
        limits=api.ResourcesRequirements(cpu=2.0),
        requests=api.ResourcesRequirements(cpu=1.0),
    )
    container_spec = ContainerSpecFactory.build(resources=container_resources_requirements)
    api_pod = APIPodFactory.build(spec=PodSpecFactory.build(containers=[container_spec]))
    deployment = PodOwner(pods=[api_pod])
    cpu_resources = deployment.cpu_resources()
    assert cpu_resources.count_total == 1
    assert cpu_resources.limit == 2.0
    assert cpu_resources.request == 1.0


def test_deployment_pod_resources_one_pod_per_phase() -> None:
    # Assemble
    deployment = PodOwner(
        pods=[
            APIPodFactory.build(status=PodStatusFactory.build(phase=phase)) for phase in api.Phase
        ],
    )

    # Act
    pod_resources = deployment.pod_resources()

    # Assert
    for _phase, pods in pod_resources:
        assert len(pods) == 1
