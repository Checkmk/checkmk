#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence
from unittest.mock import MagicMock, Mock

import pytest

from tests.unit.cmk.special_agents.agent_kube.factory import (
    api_to_agent_node,
    APINodeFactory,
    APIPodFactory,
    ContainerStatusFactory,
    create_container_state,
    node_status,
    NodeResourcesFactory,
    NodeStatusFactory,
)

import cmk.special_agents.utils_kubernetes.agent_handlers.common
from cmk.special_agents import agent_kube as agent
from cmk.special_agents.utils_kubernetes.schemata import api, section


def nodes_api_sections() -> Sequence[str]:
    return [
        "kube_node_container_count_v1",
        "kube_node_kubelet_v1",
        "kube_pod_resources_v1",
        "kube_allocatable_pods_v1",
        "kube_node_info_v1",
        "kube_cpu_resources_v1",
        "kube_memory_resources_v1",
        "kube_allocatable_cpu_resource_v1",
        "kube_allocatable_memory_resource_v1",
        "kube_node_conditions_v1",
        "kube_node_custom_conditions_v1",
    ]


def test_node_allocatable_memory_resource() -> None:
    memory = 2.0 * 1024
    status = NodeStatusFactory.build(
        allocatable=NodeResourcesFactory.build(memory=memory, factory_use_construct=True)
    )
    node = api_to_agent_node(APINodeFactory.build(status=status))
    expected = section.AllocatableResource(context="node", value=memory)
    actual = node.allocatable_memory_resource()
    assert actual == expected


def test_node_allocatable_cpu_resource() -> None:
    cpu = 2.0
    status = NodeStatusFactory.build(
        allocatable=NodeResourcesFactory.build(cpu=cpu, factory_use_construct=True)
    )
    node = api_to_agent_node(APINodeFactory.build(status=status))
    expected = section.AllocatableResource(context="node", value=cpu)
    actual = node.allocatable_cpu_resource()
    assert actual == expected


def test_node_alloctable_pods() -> None:
    capacity = 2
    allocatable = 3
    status = NodeStatusFactory.build(
        allocatable=NodeResourcesFactory.build(pods=allocatable, factory_use_construct=True),
        capacity=NodeResourcesFactory.build(pods=capacity, factory_use_construct=True),
    )
    node = api_to_agent_node(APINodeFactory.build(status=status))
    expected = section.AllocatablePods(capacity=capacity, allocatable=allocatable)
    actual = node.allocatable_pods()
    assert actual == expected


def test_write_nodes_api_sections_registers_sections_to_be_written(
    write_sections_mock: MagicMock,
) -> None:
    node = api_to_agent_node(APINodeFactory.build())
    agent.write_nodes_api_sections(
        [node],
        agent.CheckmkHostSettings(
            cluster_name="cluster",
            kubernetes_cluster_hostname="host",
            annotation_key_pattern=cmk.special_agents.utils_kubernetes.agent_handlers.common.AnnotationNonPatternOption.ignore_all,
        ),
        Mock(),
    )
    assert list(write_sections_mock.call_args[0][0]) == nodes_api_sections()


def test_write_nodes_api_sections_maps_section_names_to_callables(
    write_sections_mock: MagicMock,
) -> None:
    node = api_to_agent_node(APINodeFactory.build())
    agent.write_nodes_api_sections(
        [node],
        agent.CheckmkHostSettings(
            cluster_name="cluster",
            kubernetes_cluster_hostname="host",
            annotation_key_pattern=cmk.special_agents.utils_kubernetes.agent_handlers.common.AnnotationNonPatternOption.ignore_all,
        ),
        Mock(),
    )
    assert all(
        callable(write_sections_mock.call_args[0][0][section_name])
        for section_name in nodes_api_sections()
    )


def test_write_nodes_api_sections_calls_write_sections_for_each_node(
    write_sections_mock: MagicMock,
) -> None:
    cluster_nodes = 3
    agent.write_nodes_api_sections(
        [api_to_agent_node(APINodeFactory.build()) for _ in range(cluster_nodes)],
        agent.CheckmkHostSettings(
            cluster_name="cluster",
            kubernetes_cluster_hostname="host",
            annotation_key_pattern=cmk.special_agents.utils_kubernetes.agent_handlers.common.AnnotationNonPatternOption.ignore_all,
        ),
        Mock(),
    )
    assert write_sections_mock.call_count == cluster_nodes


def test_conditions_returns_all_native_conditions() -> None:
    node = api_to_agent_node(APINodeFactory.build(status=node_status(api.NodeConditionStatus.TRUE)))
    conditions = node.conditions()
    assert conditions is not None
    conditions_dict = conditions.dict()
    assert len(conditions_dict) == len(
        cmk.special_agents.utils_kubernetes.agent_handlers.common.NATIVE_NODE_CONDITION_TYPES
    )
    assert all(
        condition_type.lower() in conditions_dict
        for condition_type in cmk.special_agents.utils_kubernetes.agent_handlers.common.NATIVE_NODE_CONDITION_TYPES
    )


def test_conditions_respects_status_conditions() -> None:
    status = node_status(api.NodeConditionStatus.TRUE)
    node = api_to_agent_node(APINodeFactory.build(status=status))
    assert status.conditions is not None

    native_conditions = [
        cond
        for cond in status.conditions
        if cond.type_
        in cmk.special_agents.utils_kubernetes.agent_handlers.common.NATIVE_NODE_CONDITION_TYPES
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
        if cond.type_
        not in cmk.special_agents.utils_kubernetes.agent_handlers.common.NATIVE_NODE_CONDITION_TYPES
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
    info = node.info(
        "cluster",
        "host",
        cmk.special_agents.utils_kubernetes.agent_handlers.common.AnnotationNonPatternOption.ignore_all,
    )
    assert info.name == node.metadata.name
    assert info.labels == node.metadata.labels
    assert isinstance(info.creation_timestamp, float)


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
