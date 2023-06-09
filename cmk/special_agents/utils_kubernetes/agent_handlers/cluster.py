#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from cmk.special_agents.utils_kubernetes.agent_handlers.common import (
    _node_collector_replicas,
    Cluster,
    collect_cpu_resources_from_api_pods,
    collect_memory_resources_from_api_pods,
    pod_resources_from_api_pods,
)
from cmk.special_agents.utils_kubernetes.schemata import api, section


def pod_resources(api_cluster: Cluster) -> section.PodResources:
    return pod_resources_from_api_pods(api_cluster.aggregation_pods)


def allocatable_pods(api_cluster: Cluster) -> section.AllocatablePods:
    return section.AllocatablePods(
        capacity=sum(node.status.capacity.pods for node in api_cluster.aggregation_nodes),
        allocatable=sum(node.status.allocatable.pods for node in api_cluster.aggregation_nodes),
    )


def node_count(api_cluster: Cluster) -> section.NodeCount:
    return section.NodeCount(
        nodes=[
            section.CountableNode(
                ready=node_is_ready(node),
                roles=node.roles(),
            )
            for node in api_cluster.nodes
        ]
    )


def memory_resources(api_cluster: Cluster) -> section.Resources:
    return collect_memory_resources_from_api_pods(api_cluster.aggregation_pods)


def cpu_resources(api_cluster: Cluster) -> section.Resources:
    return collect_cpu_resources_from_api_pods(api_cluster.aggregation_pods)


def allocatable_memory_resource(api_cluster: Cluster) -> section.AllocatableResource:
    return section.AllocatableResource(
        context="cluster",
        value=sum(node.status.allocatable.memory for node in api_cluster.aggregation_nodes),
    )


def allocatable_cpu_resource(api_cluster: Cluster) -> section.AllocatableResource:
    return section.AllocatableResource(
        context="cluster",
        value=sum(node.status.allocatable.cpu for node in api_cluster.aggregation_nodes),
    )


def version(api_cluster: Cluster) -> api.GitVersion:
    return api_cluster.cluster_details.version


def node_collector_daemons(api_cluster: Cluster) -> section.CollectorDaemons:
    return _node_collector_daemons(api_cluster.daemonsets)


def node_is_ready(node: api.Node) -> bool:
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
