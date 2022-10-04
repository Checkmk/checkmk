#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Sequence
from unittest.mock import Mock

import pytest

from tests.unit.cmk.special_agents.agent_kube.factory import (
    api_to_agent_node,
    APINodeFactory,
    APIPodFactory,
    ContainerResourcesFactory,
    ContainerSpecFactory,
    ContainerStatusFactory,
    create_container_state,
    node_status,
    NodeResourcesFactory,
    NodeStatusFactory,
    PodSpecFactory,
    PodStatusFactory,
)

from cmk.special_agents import agent_kube as agent
from cmk.special_agents.utils_kubernetes.schemata import api, section


@pytest.mark.parametrize("node_pods", [0, 10, 20])
def test_node_pod_resources_returns_all_node_pods(node_pods: int) -> None:
    node = api_to_agent_node(
        APINodeFactory.build(),
        pods=APIPodFactory.batch(size=node_pods),
    )
    resources = dict(node.pod_resources())
    pod_resources = section.PodResources(**resources)
    assert sum(len(pods) for _, pods in pod_resources) == node_pods


def test_node_pod_resources_one_pod_per_phase() -> None:
    node = api_to_agent_node(
        APINodeFactory.build(),
        pods=[
            APIPodFactory.build(status=PodStatusFactory.build(phase=phase)) for phase in api.Phase
        ],
    )
    resources = dict(node.pod_resources())
    pod_resources = section.PodResources(**resources)
    for _phase, pods in pod_resources:
        assert len(pods) == 1


@pytest.mark.parametrize("phase", ["running", "pending", "succeeded", "failed", "unknown"])
def test_node_pod_resources_pods_in_phase(
    phase: str,
) -> None:
    node = api_to_agent_node(
        APINodeFactory.build(),
        pods=APIPodFactory.batch(size=len(api.Phase), status=PodStatusFactory.build(phase=phase)),
    )
    pods = node.pods(api.Phase(phase))
    assert len(pods) == len(api.Phase)


@pytest.mark.parametrize("phase", ["running", "pending", "succeeded", "failed", "unknown"])
def test_node_pod_resources_pods_in_phase_no_phase_param(phase: str) -> None:
    node = api_to_agent_node(
        APINodeFactory.build(),
        pods=APIPodFactory.batch(size=len(api.Phase), status=PodStatusFactory.build(phase=phase)),
    )
    pods = node.pods()
    assert len(pods) == len(api.Phase)


def test_node_allocatable_memory_resource() -> None:
    memory = 2.0 * 1024
    resources = {
        "capacity": NodeResourcesFactory.build(),
        "allocatable": NodeResourcesFactory.build(memory=memory),
    }
    node = api_to_agent_node(APINodeFactory.build(resources=resources))
    expected = section.AllocatableResource(context="node", value=memory)
    actual = node.allocatable_memory_resource()
    assert actual == expected


def test_node_allocatable_cpu_resource() -> None:
    cpu = 2.0
    resources = {
        "capacity": NodeResourcesFactory.build(),
        "allocatable": NodeResourcesFactory.build(cpu=cpu),
    }
    node = api_to_agent_node(APINodeFactory.build(resources=resources))
    expected = section.AllocatableResource(context="node", value=cpu)
    actual = node.allocatable_cpu_resource()
    assert actual == expected


def test_node_alloctable_pods() -> None:
    capacity = 2
    allocatable = 3
    resources = {
        "capacity": NodeResourcesFactory.build(pods=capacity),
        "allocatable": NodeResourcesFactory.build(pods=allocatable),
    }
    node = api_to_agent_node(APINodeFactory.build(resources=resources))
    expected = section.AllocatablePods(capacity=capacity, allocatable=allocatable)
    actual = node.allocatable_pods()
    assert actual == expected


def test_write_nodes_api_sections_registers_sections_to_be_written(  # type:ignore[no-untyped-def]
    nodes_api_sections: Sequence[str], write_sections_mock
) -> None:
    node = api_to_agent_node(APINodeFactory.build())
    agent.write_nodes_api_sections(
        "cluster", agent.AnnotationNonPatternOption.ignore_all, [node], "host", Mock()
    )
    assert list(write_sections_mock.call_args[0][0]) == nodes_api_sections


def test_write_nodes_api_sections_maps_section_names_to_callables(  # type:ignore[no-untyped-def]
    nodes_api_sections: Sequence[str], write_sections_mock
):
    node = api_to_agent_node(APINodeFactory.build())
    agent.write_nodes_api_sections(
        "cluster", agent.AnnotationNonPatternOption.ignore_all, [node], "host", Mock()
    )
    assert all(
        callable(write_sections_mock.call_args[0][0][section_name])
        for section_name in nodes_api_sections
    )


def test_write_nodes_api_sections_calls_write_sections_for_each_node(  # type:ignore[no-untyped-def]
    write_sections_mock,
):
    cluster_nodes = 3
    agent.write_nodes_api_sections(
        "cluster",
        agent.AnnotationNonPatternOption.ignore_all,
        [api_to_agent_node(APINodeFactory.build()) for _ in range(cluster_nodes)],
        "host",
        Mock(),
    )
    assert write_sections_mock.call_count == cluster_nodes


def test_conditions_returns_all_native_conditions() -> None:
    node = api_to_agent_node(APINodeFactory.build(status=node_status(api.NodeConditionStatus.TRUE)))
    conditions = node.conditions()
    assert conditions is not None
    conditions_dict = conditions.dict()
    assert len(conditions_dict) == len(agent.NATIVE_NODE_CONDITION_TYPES)
    assert all(
        condition_type.lower() in conditions_dict
        for condition_type in agent.NATIVE_NODE_CONDITION_TYPES
    )


def test_conditions_respects_status_conditions() -> None:
    status = node_status(api.NodeConditionStatus.TRUE)
    node = api_to_agent_node(APINodeFactory.build(status=status))
    assert status.conditions is not None

    native_conditions = [
        cond for cond in status.conditions if cond.type_ in agent.NATIVE_NODE_CONDITION_TYPES
    ]

    conditions = node.conditions()
    assert conditions is not None
    conditions_dict = conditions.dict()
    assert len(conditions_dict) == len(native_conditions)
    assert all(
        conditions_dict[condition.type_.lower()]["status"] == condition.status
        for condition in native_conditions
    )


def test_custom_conditions_respects_status_conditions() -> None:
    status = node_status(api.NodeConditionStatus.TRUE)
    node = api_to_agent_node(APINodeFactory.build(status=status))
    assert status.conditions is not None

    npd_conditions_status = [
        cond.status
        for cond in sorted(status.conditions, key=lambda cond: cond.type_)
        if cond.type_ not in agent.NATIVE_NODE_CONDITION_TYPES
    ]

    node_custom_conditions = node.custom_conditions()
    assert node_custom_conditions is not None
    custom_conditions_status = [
        cond.status
        for cond in sorted(node_custom_conditions.custom_conditions, key=lambda cond: cond.type_)
    ]
    assert npd_conditions_status == custom_conditions_status


def test_conditions_truthy_vs_status() -> None:
    status = node_status(api.NodeConditionStatus.TRUE)
    node = api_to_agent_node(APINodeFactory.build(status=status))
    conditions = node.conditions()
    assert conditions is not None

    truthy_conditions = [c for _, c in conditions if isinstance(c, section.TruthyNodeCondition)]
    assert len(truthy_conditions) > 0
    assert all(c.is_ok() is (c.status == api.NodeConditionStatus.TRUE) for c in truthy_conditions)


def test_conditions_falsy_vs_status() -> None:
    status = node_status(api.NodeConditionStatus.TRUE)
    conditions = api_to_agent_node(APINodeFactory.build(status=status)).conditions()
    assert conditions is not None

    falsy_conditions = [c for _, c in conditions if isinstance(c, section.FalsyNodeCondition)]
    assert len(falsy_conditions) > 0
    assert all(c.is_ok() is (c.status == api.NodeConditionStatus.FALSE) for c in falsy_conditions)


def test_conditions_with_status_conditions_none() -> None:
    conditions = api_to_agent_node(
        APINodeFactory.build(status=NodeStatusFactory.build(conditions=None))
    ).conditions()
    assert conditions is None


def test_node_info_section() -> None:
    node = api_to_agent_node(APINodeFactory.build())
    info = node.info("cluster", "host", agent.AnnotationNonPatternOption.ignore_all)
    assert info.name == node.metadata.name
    assert info.labels == node.metadata.labels
    assert isinstance(info.creation_timestamp, float)


def test_node_memory_resources() -> None:
    container_resources_requirements = ContainerResourcesFactory.build(
        limits=api.ResourcesRequirements(memory=2.0 * 1024),
        requests=api.ResourcesRequirements(memory=1.0 * 1024),
    )
    container_spec = ContainerSpecFactory.build(resources=container_resources_requirements)
    node = api_to_agent_node(
        APINodeFactory.build(),
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
    node = api_to_agent_node(
        APINodeFactory.build(),
        pods=[APIPodFactory.build(spec=PodSpecFactory.build(containers=[container_spec]))],
    )
    cpu_resources = node.cpu_resources()
    assert cpu_resources.count_total == 1
    assert cpu_resources.limit == 2.0
    assert cpu_resources.request == 1.0


@pytest.mark.parametrize("pod_containers_count", [0, 5, 10])
@pytest.mark.parametrize("container_status_state", list(api.ContainerStateType))
def test_node_container_count(
    container_status_state: api.ContainerStateType, pod_containers_count: int
) -> None:
    containers = {}
    for _ in range(pod_containers_count):
        c = ContainerStatusFactory.build(state=create_container_state(state=container_status_state))
        containers[c.name] = c
    node = api_to_agent_node(
        APINodeFactory.build(), pods=[APIPodFactory.build(containers=containers)]
    )
    container_count = node.container_count()
    assert isinstance(container_count, section.ContainerCount)
    assert container_count.dict()[container_status_state.value] == pod_containers_count
    assert all(
        count == 0
        for state, count in container_count.dict().items()
        if state != container_status_state.value
    )
