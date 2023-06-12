#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from unittest.mock import MagicMock

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

from cmk.special_agents.utils_kubernetes.agent_handlers.common import (
    AnnotationNonPatternOption,
    CheckmkHostSettings,
)
from cmk.special_agents.utils_kubernetes.agent_handlers.node import (
    _allocatable_cpu_resource,
    _allocatable_memory_resource,
    _allocatable_pods,
    _conditions,
    _container_count,
    _custom_conditions,
    _info,
    create_api_sections,
    NATIVE_NODE_CONDITION_TYPES,
)
from cmk.special_agents.utils_kubernetes.schemata import api, section


def api_nodes_api_sections() -> set[str]:
    return {
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
    }


def test_api_node_allocatable_memory_resource() -> None:
    memory = 2.0 * 1024
    status = NodeStatusFactory.build(
        allocatable=NodeResourcesFactory.build(memory=memory, factory_use_construct=True)
    )
    api_node = api_to_agent_node(APINodeFactory.build(status=status))
    expected = section.AllocatableResource(context="node", value=memory)
    actual = _allocatable_memory_resource(api_node)
    assert actual == expected


def test_api_node_allocatable_cpu_resource() -> None:
    cpu = 2.0
    status = NodeStatusFactory.build(
        allocatable=NodeResourcesFactory.build(cpu=cpu, factory_use_construct=True)
    )
    api_node = api_to_agent_node(APINodeFactory.build(status=status))
    expected = section.AllocatableResource(context="node", value=cpu)
    actual = _allocatable_cpu_resource(api_node)
    assert actual == expected


def test_api_node_alloctable_pods() -> None:
    capacity = 2
    allocatable = 3
    status = NodeStatusFactory.build(
        allocatable=NodeResourcesFactory.build(pods=allocatable, factory_use_construct=True),
        capacity=NodeResourcesFactory.build(pods=capacity, factory_use_construct=True),
    )
    api_node = api_to_agent_node(APINodeFactory.build(status=status))
    expected = section.AllocatablePods(capacity=capacity, allocatable=allocatable)
    actual = _allocatable_pods(api_node)
    assert actual == expected


def test_write_api_nodes_api_sections_registers_sections_to_be_written(
    write_sections_mock: MagicMock,
) -> None:
    api_node = api_to_agent_node(APINodeFactory.build())
    sections = create_api_sections(
        api_node,
        CheckmkHostSettings(
            cluster_name="cluster",
            kubernetes_cluster_hostname="host",
            annotation_key_pattern=AnnotationNonPatternOption.ignore_all,
        ),
        "node",
    )
    assert set(s.section_name for s in sections) == api_nodes_api_sections()


def test_conditions_returns_all_native_conditions() -> None:
    api_node = api_to_agent_node(
        APINodeFactory.build(status=node_status(api.NodeConditionStatus.TRUE))
    )
    node_conditions = _conditions(api_node)
    assert node_conditions is not None
    conditions_dict = node_conditions.dict()
    assert len(conditions_dict) == len(NATIVE_NODE_CONDITION_TYPES)
    assert all(
        condition_type.lower() in conditions_dict for condition_type in NATIVE_NODE_CONDITION_TYPES
    )


def test_conditions_respects_status_conditions() -> None:
    status = node_status(api.NodeConditionStatus.TRUE)
    api_node = api_to_agent_node(APINodeFactory.build(status=status))
    assert status.conditions is not None

    native_conditions = [
        cond for cond in status.conditions if cond.type_ in NATIVE_NODE_CONDITION_TYPES
    ]

    node_conditions = _conditions(api_node)
    assert node_conditions is not None
    conditions_dict = node_conditions.dict()
    assert len(conditions_dict) == len(native_conditions)
    assert all(
        conditions_dict[condition.type_.lower()]["status"] == condition.status
        for condition in native_conditions
    )


def test_custom_conditions_respects_status_conditions() -> None:
    status = node_status(api.NodeConditionStatus.TRUE)
    api_node = api_to_agent_node(APINodeFactory.build(status=status))
    assert status.conditions is not None

    npd_conditions_status = [
        cond.status
        for cond in sorted(status.conditions, key=lambda cond: cond.type_)
        if cond.type_ not in NATIVE_NODE_CONDITION_TYPES
    ]

    api_node_custom_conditions = _custom_conditions(api_node)
    assert api_node_custom_conditions is not None
    custom_conditions_status = [
        cond.status
        for cond in sorted(
            api_node_custom_conditions.custom_conditions, key=lambda cond: cond.type_
        )
    ]
    assert npd_conditions_status == custom_conditions_status


def test_conditions_truthy_vs_status() -> None:
    status = node_status(api.NodeConditionStatus.TRUE)
    api_node = api_to_agent_node(APINodeFactory.build(status=status))
    node_conditions = _conditions(api_node)
    assert node_conditions is not None

    truthy_conditions = [
        c for _, c in node_conditions if isinstance(c, section.TruthyNodeCondition)
    ]
    assert len(truthy_conditions) > 0
    assert all(c.is_ok() is (c.status == api.NodeConditionStatus.TRUE) for c in truthy_conditions)


def test_conditions_falsy_vs_status() -> None:
    status = node_status(api.NodeConditionStatus.TRUE)
    api_node = api_to_agent_node(APINodeFactory.build(status=status))
    node_conditions = _conditions(api_node)
    assert node_conditions is not None

    falsy_conditions = [c for _, c in node_conditions if isinstance(c, section.FalsyNodeCondition)]
    assert len(falsy_conditions) > 0
    assert all(c.is_ok() is (c.status == api.NodeConditionStatus.FALSE) for c in falsy_conditions)


def test_conditions_with_status_conditions_none() -> None:
    api_node = api_to_agent_node(
        APINodeFactory.build(status=NodeStatusFactory.build(conditions=None))
    )
    node_conditions = _conditions(api_node)
    assert node_conditions is None


def test_api_node_info_section() -> None:
    api_node = api_to_agent_node(APINodeFactory.build())
    node_info = _info(
        api_node,
        "cluster",
        "host",
        AnnotationNonPatternOption.ignore_all,
    )
    assert node_info.name == api_node.metadata.name
    assert node_info.labels == api_node.metadata.labels
    assert isinstance(node_info.creation_timestamp, float)


@pytest.mark.parametrize("pod_containers_count", [0, 5, 10])
@pytest.mark.parametrize("container_status_state", list(api.ContainerStateType))
def test_api_node_container_count(
    container_status_state: api.ContainerStateType, pod_containers_count: int
) -> None:
    containers = {}
    for _ in range(pod_containers_count):
        c = ContainerStatusFactory.build(state=create_container_state(state=container_status_state))
        containers[c.name] = c
    api_node = api_to_agent_node(
        APINodeFactory.build(), pods=[APIPodFactory.build(containers=containers)]
    )
    node_container_count = _container_count(api_node)
    assert isinstance(node_container_count, section.ContainerCount)
    assert node_container_count.dict()[container_status_state.value] == pod_containers_count
    assert all(
        count == 0
        for state, count in node_container_count.dict().items()
        if state != container_status_state.value
    )
