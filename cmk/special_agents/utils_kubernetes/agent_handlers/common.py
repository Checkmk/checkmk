#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import enum
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Collection, Iterable, Literal, Sequence

from cmk.special_agents.utils_kubernetes.api_server import APIData
from cmk.special_agents.utils_kubernetes.schemata import api, section


class AnnotationNonPatternOption(enum.Enum):
    ignore_all = "ignore_all"
    import_all = "import_all"


AnnotationOption = (
    str | Literal[AnnotationNonPatternOption.ignore_all, AnnotationNonPatternOption.import_all]
)


@dataclass(frozen=True)
class PodOwner:
    pods: Sequence[api.Pod]

    def pod_resources(self) -> section.PodResources:
        return pod_resources_from_api_pods(self.pods)

    def memory_resources(self) -> section.Resources:
        return collect_memory_resources_from_api_pods(self.pods)

    def cpu_resources(self) -> section.Resources:
        return collect_cpu_resources_from_api_pods(self.pods)


def aggregate_resources(
    resource_type: Literal["memory", "cpu"], containers: Collection[api.ContainerSpec]
) -> section.Resources:
    specified_requests = [
        request
        for c in containers
        if (request := getattr(c.resources.requests, resource_type)) is not None
    ]
    specified_limits = [
        limit
        for c in containers
        if (limit := getattr(c.resources.limits, resource_type)) is not None
    ]

    count_total = len(containers)

    return section.Resources(
        request=sum(specified_requests),
        limit=sum(specified_limits),
        count_unspecified_requests=count_total - len(specified_requests),
        count_unspecified_limits=count_total - len(specified_limits),
        count_zeroed_limits=sum(1 for x in specified_limits if x == 0),
        count_total=count_total,
    )


def thin_containers(pods: Collection[api.Pod]) -> section.ThinContainers:
    containers: list[api.ContainerStatus] = []
    for pod in pods:
        if container_map := pod.containers:
            containers.extend(container_map.values())
    return section.ThinContainers(
        images=frozenset(container.image for container in containers),
        names=[api.ContainerName(container.name) for container in containers],
    )


def collect_memory_resources_from_api_pods(pods: Sequence[api.Pod]) -> section.Resources:
    return aggregate_resources("memory", [c for pod in pods for c in pod.spec.containers])


def collect_cpu_resources_from_api_pods(pods: Sequence[api.Pod]) -> section.Resources:
    return aggregate_resources("cpu", [c for pod in pods for c in pod.spec.containers])


def pod_resources_from_api_pods(pods: Sequence[api.Pod]) -> section.PodResources:
    resources: defaultdict[str, list[str]] = defaultdict(list)
    for pod in pods:
        resources[pod.status.phase].append(pod_name(pod))
    return section.PodResources(**resources)


def pod_name(pod: api.Pod, prepend_namespace: bool = False) -> str:
    if not prepend_namespace:
        return pod.metadata.name

    return f"{pod.metadata.namespace}_{pod.metadata.name}"


def filter_annotations_by_key_pattern(
    annotations: api.Annotations,
    annotation_key_pattern: AnnotationOption,
) -> section.FilteredAnnotations:
    """Match annotation against pattern from Kubernetes rule.

    >>> annotations = {
    ...   "app": "",
    ...   "start_cmk": "",
    ...   "cmk_end": "",
    ...   "cmk": "",
    ... }
    >>> filter_annotations_by_key_pattern(annotations, AnnotationNonPatternOption.ignore_all) == {}
    True
    >>> filter_annotations_by_key_pattern(annotations, AnnotationNonPatternOption.import_all) == annotations
    True
    >>> filter_annotations_by_key_pattern(annotations, "cmk")  # infix regex, see below
    {'start_cmk': '', 'cmk_end': '', 'cmk': ''}
    """
    if annotation_key_pattern == AnnotationNonPatternOption.ignore_all:
        return section.FilteredAnnotations({})
    if annotation_key_pattern == AnnotationNonPatternOption.import_all:
        return section.FilteredAnnotations(annotations)
    return section.FilteredAnnotations(
        {key: value for key, value in annotations.items() if re.search(annotation_key_pattern, key)}
    )


def pod_lifecycle_phase(pod_status: api.PodStatus) -> section.PodLifeCycle:
    return section.PodLifeCycle(phase=pod_status.phase)


def namespace_name(api_namespace: api.Namespace) -> api.NamespaceName:
    """The name of the namespace
    Examples:
        >>> metadata = api.NamespaceMetaData.parse_obj({"name": "foo", "creation_timestamp": "2021-05-04T09:01:13Z", "labels": {}, "annotations": {}})
        >>> namespace = api.Namespace(metadata=metadata)
        >>> namespace_name(namespace)
        'foo'
    """
    return api_namespace.metadata.name


NATIVE_NODE_CONDITION_TYPES = [
    "Ready",
    "MemoryPressure",
    "DiskPressure",
    "PIDPressure",
    "NetworkUnavailable",
]


@dataclass(frozen=True)
class Node(PodOwner):
    metadata: api.NodeMetaData
    status: api.NodeStatus
    kubelet_health: api.HealthZ

    def allocatable_pods(self) -> section.AllocatablePods:
        return section.AllocatablePods(
            capacity=self.status.capacity.pods,
            allocatable=self.status.allocatable.pods,
        )

    def kubelet(self) -> section.KubeletInfo:
        return section.KubeletInfo(
            version=self.status.node_info.kubelet_version,
            proxy_version=self.status.node_info.kube_proxy_version,
            health=self.kubelet_health,
        )

    def info(
        self,
        cluster_name: str,
        kubernetes_cluster_hostname: str,
        annotation_key_pattern: AnnotationOption,
    ) -> section.NodeInfo:
        return section.NodeInfo(
            labels=self.metadata.labels,
            annotations=filter_annotations_by_key_pattern(
                self.metadata.annotations, annotation_key_pattern
            ),
            addresses=self.status.addresses,
            name=self.metadata.name,
            creation_timestamp=self.metadata.creation_timestamp,
            architecture=self.status.node_info.architecture,
            kernel_version=self.status.node_info.kernel_version,
            os_image=self.status.node_info.os_image,
            operating_system=self.status.node_info.operating_system,
            container_runtime_version=self.status.node_info.container_runtime_version,
            cluster=cluster_name,
            kubernetes_cluster_hostname=kubernetes_cluster_hostname,
        )

    def container_count(self) -> section.ContainerCount:
        type_count = Counter(
            container.state.type.name for pod in self.pods for container in pod.containers.values()
        )
        return section.ContainerCount(**type_count)

    def allocatable_memory_resource(self) -> section.AllocatableResource:
        return section.AllocatableResource(
            context="node",
            value=self.status.allocatable.memory,
        )

    def allocatable_cpu_resource(self) -> section.AllocatableResource:
        return section.AllocatableResource(
            context="node",
            value=self.status.allocatable.cpu,
        )

    def conditions(self) -> section.NodeConditions | None:
        if not self.status.conditions:
            return None

        return section.NodeConditions.parse_obj(
            {
                condition.type_.lower(): section.NodeCondition.parse_obj(condition)
                for condition in self.status.conditions
                if condition.type_ in NATIVE_NODE_CONDITION_TYPES
            }
        )

    def custom_conditions(self) -> section.NodeCustomConditions | None:
        if not self.status.conditions:
            return None

        return section.NodeCustomConditions(
            custom_conditions=[
                section.FalsyNodeCustomCondition.parse_obj(condition)
                for condition in self.status.conditions
                if condition.type_ not in NATIVE_NODE_CONDITION_TYPES
            ]
        )


def any_match_from_list_of_infix_patterns(infix_patterns: Sequence[str], string: str) -> bool:
    """Matching consistent with RegExp.infix.

    The inline help for the RegExp.infix option reads:
        The pattern is applied as infix search. Add a leading <tt>^</tt>
        to make it match from the beginning and/or a tailing <tt>$</tt>
        to match till the end of the text.
    any_match_from_list_of_infix_patterns is consistent with this help text, if
    used with a list infix patterns.

    >>> any_match_from_list_of_infix_patterns(["start"], "start_middle_end")
    True
    >>> any_match_from_list_of_infix_patterns(["middle"], "start_middle_end")
    True
    >>> any_match_from_list_of_infix_patterns(["end"], "start_middle_end")
    True
    >>> any_match_from_list_of_infix_patterns(["middle", "no_match"], "start_middle_end")
    True
    >>> any_match_from_list_of_infix_patterns([], "start_middle_end")
    False
    >>> any_match_from_list_of_infix_patterns(["^middle"], "start_middle_end")
    False
    """
    return any(re.search(pattern, string) for pattern in infix_patterns)


def _node_is_ready(node: api.Node) -> bool:
    for condition in node.status.conditions or []:
        if condition.type_.lower() == "ready":
            return condition.status == api.NodeConditionStatus.TRUE
    return False


@dataclass(frozen=True)
class Cluster:
    cluster_details: api.ClusterDetails
    daemonsets: Sequence[api.DaemonSet]
    nodes: Sequence[api.Node]
    aggregation_pods: Sequence[api.Pod]
    aggregation_nodes: Sequence[api.Node]

    @classmethod
    def from_api_resources(cls, excluded_node_roles: Sequence[str], api_data: APIData) -> Cluster:
        aggregation_nodes = [
            api_node
            for api_node in api_data.nodes
            if not any(
                any_match_from_list_of_infix_patterns(excluded_node_roles, role)
                for role in api_node.roles()
            )
        ]
        aggregation_node_names = [node.metadata.name for node in aggregation_nodes]

        aggregation_pods = [
            pod
            for pod in api_data.pods
            if pod.spec.node in aggregation_node_names or pod.spec.node is None
        ]

        cluster = cls(
            cluster_details=api_data.cluster_details,
            daemonsets=api_data.daemonsets,
            nodes=api_data.nodes,
            aggregation_nodes=aggregation_nodes,
            aggregation_pods=aggregation_pods,
        )
        return cluster

    def pod_resources(self) -> section.PodResources:
        return pod_resources_from_api_pods(self.aggregation_pods)

    def allocatable_pods(self) -> section.AllocatablePods:
        return section.AllocatablePods(
            capacity=sum(node.status.capacity.pods for node in self.aggregation_nodes),
            allocatable=sum(node.status.allocatable.pods for node in self.aggregation_nodes),
        )

    def node_count(self) -> section.NodeCount:
        return section.NodeCount(
            nodes=[
                section.CountableNode(
                    ready=_node_is_ready(node),
                    roles=node.roles(),
                )
                for node in self.nodes
            ]
        )

    def memory_resources(self) -> section.Resources:
        return collect_memory_resources_from_api_pods(self.aggregation_pods)

    def cpu_resources(self) -> section.Resources:
        return collect_cpu_resources_from_api_pods(self.aggregation_pods)

    def allocatable_memory_resource(self) -> section.AllocatableResource:
        return section.AllocatableResource(
            context="cluster",
            value=sum(node.status.allocatable.memory for node in self.aggregation_nodes),
        )

    def allocatable_cpu_resource(self) -> section.AllocatableResource:
        return section.AllocatableResource(
            context="cluster",
            value=sum(node.status.allocatable.cpu for node in self.aggregation_nodes),
        )

    def version(self) -> api.GitVersion:
        return self.cluster_details.version

    def node_collector_daemons(self) -> section.CollectorDaemons:
        return _node_collector_daemons(self.daemonsets)


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


def _node_collector_replicas(
    statuses: list[api.DaemonSetStatus],
) -> section.NodeCollectorReplica | None:
    if len(statuses) != 1:
        return None
    status = statuses[0]
    return section.NodeCollectorReplica(
        available=status.number_available,
        desired=status.desired_number_scheduled,
    )
