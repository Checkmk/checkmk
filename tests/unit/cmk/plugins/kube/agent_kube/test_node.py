#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.unit.cmk.plugins.kube.agent_kube.factory import (
    api_to_agent_node,
    APINodeFactory,
    APIPodFactory,
    ContainerStatusFactory,
    create_container_state,
    NodeConditionFactory,
    NodeResourcesFactory,
    NodeStatusFactory,
)

from cmk.plugins.kube.agent_handlers.common import AnnotationNonPatternOption, CheckmkHostSettings
from cmk.plugins.kube.agent_handlers.node_handler import (
    _allocatable_cpu_resource,
    _allocatable_memory_resource,
    _allocatable_pods,
    _conditions,
    _container_count,
    _info,
    create_api_sections,
)
from cmk.plugins.kube.schemata import api, section


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
        "kube_node_conditions_v2",
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


def test_write_api_nodes_api_sections_registers_sections_to_be_written() -> None:
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
    assert {s.section_name for s in sections} == api_nodes_api_sections()


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


def test_api_node_conditions() -> None:
    # Assemble
    expected_condition = NodeConditionFactory.build()
    status = NodeStatusFactory.build(conditions=[expected_condition])
    api_node = APINodeFactory.build(status=status)
    # Act
    conditions = _conditions(api_node).conditions
    assert len(conditions) == 1
    condition = conditions[0]
    assert condition.status == expected_condition.status
    assert condition.message == expected_condition.message
    assert condition.reason == expected_condition.reason
    assert condition.type_ == expected_condition.type_


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
    assert node_container_count.model_dump()[container_status_state.value] == pod_containers_count
    assert all(
        count == 0
        for state, count in node_container_count.model_dump().items()
        if state != container_status_state.value
    )
