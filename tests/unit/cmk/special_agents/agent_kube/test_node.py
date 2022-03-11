#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Callable, Sequence
from unittest.mock import Mock

import pytest

from cmk.special_agents import agent_kube as agent
from cmk.special_agents.utils_kubernetes.schemata import api, section


@pytest.mark.parametrize("node_pods", [0, 10, 20])
def test_node_pod_resources_returns_all_node_pods(node: agent.Node, node_pods: int):
    resources = dict(node.pod_resources())
    pod_resources = section.PodResources(**resources)
    assert sum(len(pods) for _, pods in pod_resources) == node_pods


def test_node_pod_resources_one_pod_per_phase(node: agent.Node):
    resources = dict(node.pod_resources())
    pod_resources = section.PodResources(**resources)
    for _phase, pods in pod_resources:
        assert len(pods) == 1


@pytest.mark.parametrize(
    "phases", [["running"], ["pending"], ["succeeded"], ["failed"], ["unknown"]]
)
def test_node_pod_resources_pods_in_phase(node: agent.Node, phases, node_pods: int):
    pods = node.pods(phases[0])
    assert len(pods) == node_pods


@pytest.mark.parametrize(
    "phases", [["running"], ["pending"], ["succeeded"], ["failed"], ["unknown"]]
)
def test_node_pod_resources_pods_in_phase_no_phase_param(node: agent.Node, node_pods: int):
    pods = node.pods()
    assert len(pods) == node_pods


def test_node_allocatable_memory_resource(node_allocatable_memory: float, node: agent.Node):
    expected = section.AllocatableResource(context="node", value=node_allocatable_memory)
    actual = node.allocatable_memory_resource()
    assert actual == expected


def test_node_allocatable_cpu_resource(node_allocatable_cpu: float, node: agent.Node):
    expected = section.AllocatableResource(context="node", value=node_allocatable_cpu)
    actual = node.allocatable_cpu_resource()
    assert actual == expected


def test_node_alloctable_pods(
    node_allocatable_pods: int, node_capacity_pods: int, node: agent.Node
):
    expected = section.AllocatablePods(
        capacity=node_capacity_pods, allocatable=node_allocatable_pods
    )
    actual = node.allocatable_pods()
    assert actual == expected


def test_write_nodes_api_sections_registers_sections_to_be_written(
    node: agent.Node, nodes_api_sections: Sequence[str], write_sections_mock
):
    agent.write_nodes_api_sections("cluster", [node], Mock())
    assert list(write_sections_mock.call_args[0][0]) == nodes_api_sections


def test_write_nodes_api_sections_maps_section_names_to_callables(
    node: agent.Node, nodes_api_sections: Sequence[str], write_sections_mock
):
    agent.write_nodes_api_sections("cluster", [node], Mock())
    assert all(
        callable(write_sections_mock.call_args[0][0][section_name])
        for section_name in nodes_api_sections
    )


def test_write_nodes_api_sections_calls_write_sections_for_each_node(
    new_node: Callable[[], agent.Node], cluster_nodes: int, write_sections_mock
):
    agent.write_nodes_api_sections("cluster", [new_node() for _ in range(cluster_nodes)], Mock())
    assert write_sections_mock.call_count == cluster_nodes


def test_conditions_returns_all_native_conditions(node: agent.Node):
    conditions = node.conditions()
    assert conditions is not None
    conditions_dict = conditions.dict()
    assert len(conditions_dict) == len(agent.NATIVE_NODE_CONDITION_TYPES)
    assert all(
        condition_type.lower() in conditions_dict
        for condition_type in agent.NATIVE_NODE_CONDITION_TYPES
    )


def test_conditions_respects_status_conditions(node: agent.Node):
    api_conditions = node.status.conditions
    assert api_conditions is not None

    native_conditions = [
        cond for cond in api_conditions if cond.type_ in agent.NATIVE_NODE_CONDITION_TYPES
    ]

    conditions = node.conditions()
    assert conditions is not None
    conditions_dict = conditions.dict()
    assert len(conditions_dict) == len(native_conditions)
    assert all(
        conditions_dict[condition.type_.lower()]["status"] == condition.status
        for condition in native_conditions
    )


def test_custom_conditions_respects_status_conditions(node: agent.Node):
    status_conditions = node.status.conditions
    assert status_conditions is not None

    npd_conditions_status = [
        cond.status
        for cond in sorted(status_conditions, key=lambda cond: cond.type_)
        if cond.type_ not in agent.NATIVE_NODE_CONDITION_TYPES
    ]

    node_custom_conditions = node.custom_conditions()
    assert node_custom_conditions is not None
    custom_conditions_status = [
        cond.status
        for cond in sorted(node_custom_conditions.custom_conditions, key=lambda cond: cond.type_)
    ]
    assert npd_conditions_status == custom_conditions_status


def test_conditions_truthy_vs_status(node: agent.Node):
    conditions = node.conditions()
    assert conditions is not None

    truthy_conditions = [c for _, c in conditions if isinstance(c, section.TruthyNodeCondition)]
    assert len(truthy_conditions) > 0
    assert all(c.is_ok() is (c.status == api.NodeConditionStatus.TRUE) for c in truthy_conditions)


def test_conditions_falsy_vs_status(node: agent.Node):
    conditions = node.conditions()
    assert conditions is not None

    falsy_conditions = [c for _, c in conditions if isinstance(c, section.FalsyNodeCondition)]
    assert len(falsy_conditions) > 0
    assert all(c.is_ok() is (c.status == api.NodeConditionStatus.FALSE) for c in falsy_conditions)


def test_conditions_with_status_conditions_none(node: agent.Node):
    node.status.conditions = None
    conditions = node.conditions()
    assert conditions is None


def test_node_info_section(node: agent.Node):
    info = node.info("cluster")
    assert info.name == node.metadata.name
    assert info.labels == node.metadata.labels
    assert isinstance(info.creation_timestamp, float)


def test_node_memory_resources(
    new_node: Callable[[], agent.Node],
    new_pod: Callable[[], agent.Pod],
    pod_containers_count: int,
    container_limit_memory: float,
    container_request_memory: float,
):
    node = new_node()
    node.add_pod(new_pod())
    memory_resources = node.memory_resources()
    assert memory_resources.count_total == pod_containers_count
    assert memory_resources.limit == pod_containers_count * container_limit_memory
    assert memory_resources.request == pod_containers_count * container_request_memory


def test_node_cpu_resources(
    new_node: Callable[[], agent.Node],
    new_pod: Callable[[], agent.Pod],
    pod_containers_count: int,
    container_limit_cpu: float,
    container_request_cpu: float,
):
    node = new_node()
    node.add_pod(new_pod())
    cpu_resources = node.cpu_resources()
    assert cpu_resources.count_total == pod_containers_count
    assert cpu_resources.limit == pod_containers_count * container_limit_cpu
    assert cpu_resources.request == pod_containers_count * container_request_cpu


@pytest.mark.parametrize("pod_containers_count", [0, 5, 10])
@pytest.mark.parametrize("container_status_state", ["running", "terminated", "waiting"])
def test_node_container_count(
    container_status_state: str,
    new_node: Callable[[], agent.Node],
    new_pod: Callable[[], agent.Pod],
    pod_containers_count: int,
):
    node = new_node()
    node.add_pod(new_pod())
    container_count = node.container_count()
    assert isinstance(container_count, section.ContainerCount)
    assert container_count.dict()[container_status_state] == pod_containers_count
    assert all(
        count == 0
        for state, count in container_count.dict().items()
        if state != container_status_state
    )
