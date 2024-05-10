#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

from collections import Counter
from collections.abc import Iterator

from cmk.plugins.kube.agent_handlers.common import (
    AnnotationOption,
    CheckmkHostSettings,
    filter_annotations_by_key_pattern,
    Node,
)
from cmk.plugins.kube.common import SectionName, WriteableSection
from cmk.plugins.kube.schemata import section

NATIVE_NODE_CONDITION_TYPES = [
    "Ready",
    "MemoryPressure",
    "DiskPressure",
    "PIDPressure",
    "NetworkUnavailable",
]


def create_api_sections(
    api_node: Node,
    host_settings: CheckmkHostSettings,
    piggyback_name: str,
) -> Iterator[WriteableSection]:
    yield from (
        WriteableSection(
            section_name=SectionName("kube_node_container_count_v1"),
            section=_container_count(api_node),
            piggyback_name=piggyback_name,
        ),
        WriteableSection(
            section_name=SectionName("kube_node_kubelet_v1"),
            section=_kubelet(api_node),
            piggyback_name=piggyback_name,
        ),
        WriteableSection(
            section_name=SectionName("kube_pod_resources_v1"),
            section=api_node.pod_resources(),
            piggyback_name=piggyback_name,
        ),
        WriteableSection(
            section_name=SectionName("kube_allocatable_pods_v1"),
            section=_allocatable_pods(api_node),
            piggyback_name=piggyback_name,
        ),
        WriteableSection(
            section_name=SectionName("kube_node_info_v1"),
            section=_info(
                api_node,
                host_settings.cluster_name,
                host_settings.kubernetes_cluster_hostname,
                host_settings.annotation_key_pattern,
            ),
            piggyback_name=piggyback_name,
        ),
        WriteableSection(
            section_name=SectionName("kube_cpu_resources_v1"),
            section=api_node.cpu_resources(),
            piggyback_name=piggyback_name,
        ),
        WriteableSection(
            section_name=SectionName("kube_memory_resources_v1"),
            section=api_node.memory_resources(),
            piggyback_name=piggyback_name,
        ),
        WriteableSection(
            section_name=SectionName("kube_allocatable_cpu_resource_v1"),
            section=_allocatable_cpu_resource(api_node),
            piggyback_name=piggyback_name,
        ),
        WriteableSection(
            section_name=SectionName("kube_allocatable_memory_resource_v1"),
            section=_allocatable_memory_resource(api_node),
            piggyback_name=piggyback_name,
        ),
        WriteableSection(
            section_name=SectionName("kube_node_conditions_v2"),
            section=_conditions(api_node),
            piggyback_name=piggyback_name,
        ),
    )


def _allocatable_pods(api_node: Node) -> section.AllocatablePods:
    return section.AllocatablePods(
        capacity=api_node.status.capacity.pods,
        allocatable=api_node.status.allocatable.pods,
    )


def _kubelet(api_node: Node) -> section.KubeletInfo:
    return section.KubeletInfo(
        version=api_node.status.node_info.kubelet_version,
        proxy_version=api_node.status.node_info.kube_proxy_version,
        health=api_node.kubelet_health,
    )


def _info(
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


def _container_count(api_node: Node) -> section.ContainerCount:
    type_count = Counter(
        container.state.type.name for pod in api_node.pods for container in pod.containers.values()
    )
    return section.ContainerCount(**type_count)


def _allocatable_memory_resource(api_node: Node) -> section.AllocatableResource:
    return section.AllocatableResource(
        context="node",
        value=api_node.status.allocatable.memory,
    )


def _allocatable_cpu_resource(api_node: Node) -> section.AllocatableResource:
    return section.AllocatableResource(
        context="node",
        value=api_node.status.allocatable.cpu,
    )


def _conditions(api_node: Node) -> section.NodeConditions:
    api_conditions = api_node.status.conditions or []
    conditions = [
        section.NodeCondition.model_validate(condition.model_dump()) for condition in api_conditions
    ]
    return section.NodeConditions(conditions=conditions)
