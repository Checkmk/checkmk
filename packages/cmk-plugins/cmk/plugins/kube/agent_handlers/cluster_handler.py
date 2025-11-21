#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Iterator

from cmk.plugins.kube.agent_handlers.common import (
    _node_collector_replicas,
    Cluster,
    collect_cpu_resources_from_api_pods,
    collect_memory_resources_from_api_pods,
    pod_resources_from_api_pods,
)
from cmk.plugins.kube.common import SectionName, WriteableSection
from cmk.plugins.kube.schemata import api, section


def create_api_sections(api_cluster: Cluster, cluster_name: str) -> Iterator[WriteableSection]:
    yield from (
        WriteableSection(
            piggyback_name="",
            section_name=SectionName("kube_pod_resources_v1"),
            section=_pod_resources(api_cluster),
        ),
        WriteableSection(
            piggyback_name="",
            section_name=SectionName("kube_allocatable_pods_v1"),
            section=_allocatable_pods(api_cluster),
        ),
        WriteableSection(
            piggyback_name="",
            section_name=SectionName("kube_node_count_v1"),
            section=_node_count(api_cluster),
        ),
        WriteableSection(
            piggyback_name="",
            section_name=SectionName("kube_cluster_details_v1"),
            section=section.ClusterDetails.model_validate(api_cluster.cluster_details.model_dump()),
        ),
        WriteableSection(
            piggyback_name="",
            section_name=SectionName("kube_memory_resources_v1"),
            section=_memory_resources(api_cluster),
        ),
        WriteableSection(
            piggyback_name="",
            section_name=SectionName("kube_cpu_resources_v1"),
            section=_cpu_resources(api_cluster),
        ),
        WriteableSection(
            piggyback_name="",
            section_name=SectionName("kube_allocatable_memory_resource_v1"),
            section=_allocatable_memory_resource(api_cluster),
        ),
        WriteableSection(
            piggyback_name="",
            section_name=SectionName("kube_allocatable_cpu_resource_v1"),
            section=_allocatable_cpu_resource(api_cluster),
        ),
        WriteableSection(
            piggyback_name="",
            section_name=SectionName("kube_cluster_info_v1"),
            section=section.ClusterInfo(name=cluster_name, version=_version(api_cluster)),
        ),
        WriteableSection(
            piggyback_name="",
            section_name=SectionName("kube_collector_daemons_v1"),
            section=_node_collector_daemons(api_cluster.daemonsets),
        ),
    )


def _pod_resources(api_cluster: Cluster) -> section.PodResources:
    return pod_resources_from_api_pods(api_cluster.aggregation_pods)


def _allocatable_pods(api_cluster: Cluster) -> section.AllocatablePods:
    return section.AllocatablePods(
        capacity=sum(node.status.capacity.pods for node in api_cluster.aggregation_nodes),
        allocatable=sum(node.status.allocatable.pods for node in api_cluster.aggregation_nodes),
    )


def _node_count(api_cluster: Cluster) -> section.NodeCount:
    return section.NodeCount(
        nodes=[
            section.CountableNode(
                ready=_node_is_ready(node),
                roles=node.roles(),
            )
            for node in api_cluster.nodes
        ]
    )


def _memory_resources(api_cluster: Cluster) -> section.Resources:
    return collect_memory_resources_from_api_pods(api_cluster.aggregation_pods)


def _cpu_resources(api_cluster: Cluster) -> section.Resources:
    return collect_cpu_resources_from_api_pods(api_cluster.aggregation_pods)


def _allocatable_memory_resource(api_cluster: Cluster) -> section.AllocatableResource:
    return section.AllocatableResource(
        context="cluster",
        value=sum(node.status.allocatable.memory for node in api_cluster.aggregation_nodes),
    )


def _allocatable_cpu_resource(api_cluster: Cluster) -> section.AllocatableResource:
    return section.AllocatableResource(
        context="cluster",
        value=sum(node.status.allocatable.cpu for node in api_cluster.aggregation_nodes),
    )


def _version(api_cluster: Cluster) -> api.GitVersion:
    return api_cluster.cluster_details.version


def _node_is_ready(node: api.Node) -> bool:
    for condition in node.status.conditions or []:
        if condition.type_.lower() == "ready":
            return condition.status == api.NodeConditionStatus.TRUE
    return False


def _node_collector_daemons(api_daemonsets: Iterable[api.DaemonSet]) -> section.CollectorDaemons:
    # Extract DaemonSets with label key `node-collector`
    collector_daemons = defaultdict(list)
    for api_daemonset in api_daemonsets:
        if (
            label := api_daemonset.metadata.labels.get(api.LabelName("node-collector"))
        ) is not None:
            collector_type = label.value
            collector_daemons[collector_type].append(api_daemonset.status)
    collector_daemons.default_factory = None

    # Only leave unknown collectors inside of `collector_daemons`
    machine_status = collector_daemons.pop(api.LabelValue("machine-sections"), [])
    container_status = collector_daemons.pop(api.LabelValue("container-metrics"), [])

    return section.CollectorDaemons(
        machine=_node_collector_replicas(machine_status),
        container=_node_collector_replicas(container_status),
        errors=section.IdentificationError(
            duplicate_machine_collector=len(machine_status) > 1,
            duplicate_container_collector=len(container_status) > 1,
            unknown_collector=len(collector_daemons) > 0,
        ),
    )
