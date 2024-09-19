#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import enum
import re
from collections import defaultdict
from collections.abc import Callable, Collection, Sequence
from dataclasses import dataclass
from typing import Literal, NamedTuple, TypeVar

from cmk.plugins.kube.api_server import APIData
from cmk.plugins.kube.schemata import api, section
from cmk.plugins.kube.schemata.api import NamespaceName


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


@dataclass(frozen=True)
class DaemonSet(PodOwner):
    metadata: api.MetaData
    spec: api.DaemonSetSpec
    status: api.DaemonSetStatus
    type_: str = "daemonset"


@dataclass(frozen=True)
class Deployment(PodOwner):
    metadata: api.MetaData
    spec: api.DeploymentSpec
    status: api.DeploymentStatus
    type_: str = "deployment"


@dataclass(frozen=True)
class StatefulSet(PodOwner):
    metadata: api.MetaData
    spec: api.StatefulSetSpec
    status: api.StatefulSetStatus
    type_: str = "statefulset"


@dataclass(frozen=True)
class Node(PodOwner):
    metadata: api.NodeMetaData
    status: api.NodeStatus
    kubelet_health: api.HealthZ | api.NodeConnectionError


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


PB_KUBE_OBJECT = (
    Cluster | api.CronJob | Deployment | DaemonSet | api.Namespace | Node | api.Pod | StatefulSet
)
PiggybackFormatter = Callable[[PB_KUBE_OBJECT], str]


KubeNamespacedObj = TypeVar(
    "KubeNamespacedObj", bound=DaemonSet | Deployment | StatefulSet | api.CronJob | api.Pod
)


def kube_object_namespace_name(kube_object: KubeNamespacedObj) -> NamespaceName:
    """The namespace name of the Kubernetes object"""
    return kube_object.metadata.namespace


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
        >>> metadata = api.NamespaceMetaData.model_validate({"name": "foo", "creation_timestamp": "2021-05-04T09:01:13Z", "labels": {}, "annotations": {}})
        >>> namespace = api.Namespace(metadata=metadata)
        >>> namespace_name(namespace)
        'foo'
    """
    return api_namespace.metadata.name


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


class CheckmkHostSettings(NamedTuple):
    """
    The listed settings apply to all Kubernetes generated piggyback hosts

        cluster:
            the given Kubernetes cluster name is prefixed to all piggyback host names
        kubernetes_cluster_hostname:
            the name of the Checkmk host which represents the cluster will be made available as
            Checkmk label
        annotation_key_pattern:
            decides what annotations of the k8 object will be translated to Checkmk labels
    """

    cluster_name: str
    kubernetes_cluster_hostname: str
    annotation_key_pattern: AnnotationOption


def controller_strategy(controller: Deployment | DaemonSet | StatefulSet) -> section.UpdateStrategy:
    return section.UpdateStrategy.model_validate(controller.spec.model_dump())


def controller_spec(controller: Deployment | DaemonSet | StatefulSet) -> section.ControllerSpec:
    return section.ControllerSpec(min_ready_seconds=controller.spec.min_ready_seconds)
