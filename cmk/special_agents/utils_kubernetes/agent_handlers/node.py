#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

from collections import Counter

from cmk.special_agents.utils_kubernetes.agent_handlers.common import (
    AnnotationOption,
    filter_annotations_by_key_pattern,
    Node,
)
from cmk.special_agents.utils_kubernetes.schemata import section

NATIVE_NODE_CONDITION_TYPES = [
    "Ready",
    "MemoryPressure",
    "DiskPressure",
    "PIDPressure",
    "NetworkUnavailable",
]


def allocatable_pods(api_node: Node) -> section.AllocatablePods:
    return section.AllocatablePods(
        capacity=api_node.status.capacity.pods,
        allocatable=api_node.status.allocatable.pods,
    )


def kubelet(api_node: Node) -> section.KubeletInfo:
    return section.KubeletInfo(
        version=api_node.status.node_info.kubelet_version,
        proxy_version=api_node.status.node_info.kube_proxy_version,
        health=api_node.kubelet_health,
    )


def info(
    api_node: Node,
    cluster_name: str,
    kubernetes_cluster_hostname: str,
    annotation_key_pattern: AnnotationOption,
) -> section.NodeInfo:
    return section.NodeInfo(
        labels=api_node.metadata.labels,
        annotations=filter_annotations_by_key_pattern(
            api_node.metadata.annotations, annotation_key_pattern
        ),
        addresses=api_node.status.addresses,
        name=api_node.metadata.name,
        creation_timestamp=api_node.metadata.creation_timestamp,
        architecture=api_node.status.node_info.architecture,
        kernel_version=api_node.status.node_info.kernel_version,
        os_image=api_node.status.node_info.os_image,
        operating_system=api_node.status.node_info.operating_system,
        container_runtime_version=api_node.status.node_info.container_runtime_version,
        cluster=cluster_name,
        kubernetes_cluster_hostname=kubernetes_cluster_hostname,
    )


def container_count(api_node: Node) -> section.ContainerCount:
    type_count = Counter(
        container.state.type.name for pod in api_node.pods for container in pod.containers.values()
    )
    return section.ContainerCount(**type_count)


def allocatable_memory_resource(api_node: Node) -> section.AllocatableResource:
    return section.AllocatableResource(
        context="node",
        value=api_node.status.allocatable.memory,
    )


def allocatable_cpu_resource(api_node: Node) -> section.AllocatableResource:
    return section.AllocatableResource(
        context="node",
        value=api_node.status.allocatable.cpu,
    )


def conditions(api_node: Node) -> section.NodeConditions | None:
    if not api_node.status.conditions:
        return None

    return section.NodeConditions.parse_obj(
        {
            condition.type_.lower(): section.NodeCondition.parse_obj(condition)
            for condition in api_node.status.conditions
            if condition.type_ in NATIVE_NODE_CONDITION_TYPES
        }
    )


def custom_conditions(api_node: Node) -> section.NodeCustomConditions | None:
    if not api_node.status.conditions:
        return None

    return section.NodeCustomConditions(
        custom_conditions=[
            section.FalsyNodeCustomCondition.parse_obj(condition)
            for condition in api_node.status.conditions
            if condition.type_ not in NATIVE_NODE_CONDITION_TYPES
        ]
    )
