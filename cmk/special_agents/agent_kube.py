#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Special agent for monitoring Kubernetes clusters. This agent is required for
monitoring data provided by the Kubernetes API and the Checkmk collectors,
which can optionally be deployed within a cluster. The agent requires
Kubernetes version v1.22 or higher. Moreover, read access to the Kubernetes API
endpoints monitored by Checkmk must be provided.
"""

# mypy: warn_return_any
# mypy: disallow_untyped_defs

from __future__ import annotations

import argparse
import contextlib
import enum
import functools
import itertools
import logging
import re
import sys
from collections import Counter, defaultdict
from collections.abc import Callable, Collection, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from itertools import chain
from typing import Literal, NamedTuple, TypeVar

import requests
import urllib3
from pydantic import parse_raw_as

import cmk.utils.password_store
import cmk.utils.paths
import cmk.utils.profile

from cmk.special_agents.utils import vcrtrace
from cmk.special_agents.utils.agent_common import ConditionalPiggybackSection, SectionWriter
from cmk.special_agents.utils_kubernetes import common, performance, prometheus_section, query
from cmk.special_agents.utils_kubernetes.api_server import APIData, from_kubernetes
from cmk.special_agents.utils_kubernetes.common import (
    LOGGER,
    lookup_name,
    Piggyback,
    PodLookupName,
    PodsToHost,
    RawMetrics,
    SectionName,
    WriteableSection,
)
from cmk.special_agents.utils_kubernetes.schemata import api, section
from cmk.special_agents.utils_kubernetes.schemata.api import NamespaceName

NATIVE_NODE_CONDITION_TYPES = [
    "Ready",
    "MemoryPressure",
    "DiskPressure",
    "PIDPressure",
    "NetworkUnavailable",
]


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


class AnnotationNonPatternOption(enum.Enum):
    ignore_all = "ignore_all"
    import_all = "import_all"


AnnotationOption = (
    str | Literal[AnnotationNonPatternOption.ignore_all, AnnotationNonPatternOption.import_all]
)


class MonitoredObject(enum.Enum):
    deployments = "deployments"
    daemonsets = "daemonsets"
    statefulsets = "statefulsets"
    namespaces = "namespaces"
    nodes = "nodes"
    pods = "pods"
    cronjobs = "cronjobs"
    cronjobs_pods = "cronjobs_pods"
    pvcs = "pvcs"


def parse_arguments(args: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--debug", action="store_true", help="Debug mode: raise Python exceptions")
    p.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Verbose mode (for even more output use -vvv)",
    )
    p.add_argument(
        "--vcrtrace",
        action=vcrtrace(filter_headers=[("authorization", "Bearer ****")]),
        help="Enables VCR tracing for the API calls",
    )
    p.add_argument(
        "--cluster",
        required=True,
        help="The name of the Kubernetes cluster",
    )
    p.add_argument(
        "--kubernetes-cluster-hostname",
        required=True,
        help="The name of the Checkmk host which represents the Kubernetes cluster (this will be "
        "the host where the Kubernetes rule has been assigned to)",
    )
    p.add_argument("--token", help="Token for that user")
    p.add_argument(
        "--monitored-objects",
        type=MonitoredObject,
        nargs="+",
        default=[
            MonitoredObject.deployments,
            MonitoredObject.daemonsets,
            MonitoredObject.statefulsets,
            MonitoredObject.pods,
            MonitoredObject.namespaces,
            MonitoredObject.nodes,
            MonitoredObject.cronjobs,
        ],
        help="The Kubernetes objects which are supposed to be monitored. Available objects: "
        "deployments, nodes, pods, daemonsets, statefulsets, cronjobs_pods",
    )
    p.add_argument(
        "--api-server-endpoint", required=True, help="API server endpoint for Kubernetes API calls"
    )
    p.add_argument(
        "--api-server-proxy",
        type=str,
        default="FROM_ENVIRONMENT",
        metavar="PROXY",
        help=(
            "HTTP proxy used to connect to the Kubernetes api server. If not set, the environment settings "
            "will be used."
        ),
    )

    p.add_argument("--verify-cert-api", action="store_true", help="Verify certificate")
    namespaces = p.add_mutually_exclusive_group()
    namespaces.add_argument(
        "--namespace-include-patterns",
        "-n",
        action="append",
        default=[],
        help="Regex patterns of namespaces to show in the output. Cannot use both include and "
        "exclude patterns",
    )
    namespaces.add_argument(
        "--namespace-exclude-patterns",
        action="append",
        default=[],
        help="Regex patterns of namespaces to exclude in the output. Cannot use both include and "
        "exclude patterns.",
    )
    p.add_argument(
        "--profile",
        metavar="FILE",
        help="Profile the performance of the agent and write the output to a file",
    )
    p.add_argument(
        "--k8s-api-connect-timeout",
        type=int,
        default=10,
        help="The timeout in seconds the special agent will wait for a "
        "connection to the Kubernetes API.",
    )
    p.add_argument(
        "--k8s-api-read-timeout",
        type=int,
        default=12,
        help="The timeout in seconds the special agent will wait for a "
        "response from the Kubernetes API.",
    )
    group = p.add_mutually_exclusive_group()
    group.add_argument(
        "--cluster-aggregation-exclude-node-roles",
        nargs="+",
        default=["control-plane", "infra"],
        dest="roles",
        help="You may find that some Nodes don't add resources to the overall "
        "workload your Cluster can handle. This option allows you to remove "
        "Nodes from aggregations on the Cluster host based on their role. A "
        "node will be omitted, if any of the listed {role}s matches a label "
        "with name 'node-role.kubernetes.io/{role}'.  This affects the "
        "following services: Memory resources, CPU resources, Pod resources. "
        "Only Services on the Cluster host are affected. By default, Nodes "
        "with role control-plane and infra are omitted.",
    )
    group.add_argument(
        "--cluster-aggregation-include-all-nodes",
        action="store_false",
        dest="roles",
        help="Services on the cluster host will not exclude nodes based on their roles.",
    )
    group_host_labels = p.add_mutually_exclusive_group()
    group_host_labels.add_argument(
        "--include-annotations-as-host-labels",
        action="store_const",
        const=AnnotationNonPatternOption.import_all,
        dest="annotation_key_pattern",
        help="By default, the agent ignores annotations. With this option, all "
        "Kubernetes annotations that are valid Kubernetes labels are written to "
        "the agent output. Specifically, it is verified that the annotation "
        "value meets the same requirements as a label value. These annotations "
        "are added as host labels to their respective piggyback host using the "
        "syntax 'cmk/kubernetes/annotation/{key}:{value}'.",
    )
    group_host_labels.add_argument(
        "--include-matching-annotations-as-host-labels",
        dest="annotation_key_pattern",
        help="You can further restrict the imported annotations by specifying "
        "a pattern which the agent searches for in the key of the annotation.",
    )
    group_host_labels.set_defaults(annotation_key_pattern=AnnotationNonPatternOption.ignore_all)

    data_endpoint = p.add_mutually_exclusive_group()
    data_endpoint.add_argument(
        "--cluster-collector-endpoint",
        help="Endpoint to query metrics from Kubernetes cluster agent",
    )
    data_endpoint.add_argument(
        "--prometheus-endpoint",
        help="The full URL to the Prometheus API endpoint including the protocol (http or https). "
        "OpenShift exposes such endpoints via a route in the openshift-monitoring namespace called "
        "prometheus-k8s.",
    )
    p.add_argument(
        "--usage-connect-timeout",
        type=int,
        default=10,
        help="The timeout in seconds the special agent will wait for a "
        "connection to the endpoint specified by --prometheus-endpoint or "
        "--cluster-collector-endpoint.",
    )
    p.add_argument(
        "--usage-read-timeout",
        type=int,
        default=12,
        help="The timeout in seconds the special agent will wait for a "
        "response from the endpoint specified by --prometheus-endpoint or "
        "--cluster-collector-endpoint.",
    )
    p.add_argument(
        "--usage-proxy",
        type=str,
        default="FROM_ENVIRONMENT",
        metavar="PROXY",
        help=(
            "HTTP proxy used to connect to the endpoint specified by --prometheus-endpoint or "
            "--cluster-collector-endpoint. "
            "If not set, the environment settings will be used."
        ),
    )
    p.add_argument(
        "--usage-verify-cert",
        action="store_true",
        help="Verify certificate for the endpoint specified by --prometheus-endpoint or "
        "--cluster-collector-endpoint.",
    )
    arguments = p.parse_args(args)
    return arguments


def setup_logging(verbosity: int) -> None:
    if verbosity >= 3:
        lvl = logging.DEBUG
    elif verbosity == 2:
        lvl = logging.INFO
    elif verbosity == 1:
        lvl = logging.WARN
    else:
        logging.disable(logging.CRITICAL)
        lvl = logging.CRITICAL
    logging.basicConfig(level=lvl, format="%(asctime)s %(levelname)s %(message)s")


@dataclass(frozen=True)
class PodOwner:
    pods: Sequence[api.Pod]

    def pod_resources(self) -> section.PodResources:
        return _pod_resources_from_api_pods(self.pods)

    def memory_resources(self) -> section.Resources:
        return _collect_memory_resources_from_api_pods(self.pods)

    def cpu_resources(self) -> section.Resources:
        return _collect_cpu_resources_from_api_pods(self.pods)


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


# TODO: addition of test framework for output sections
@dataclass(frozen=True)
class Deployment(PodOwner):
    metadata: api.MetaData
    spec: api.DeploymentSpec
    status: api.DeploymentStatus
    type_: str = "deployment"


def deployment_info(
    deployment: Deployment,
    cluster_name: str,
    kubernetes_cluster_hostname: str,
    annotation_key_pattern: AnnotationOption,
) -> section.DeploymentInfo:
    return section.DeploymentInfo(
        name=deployment.metadata.name,
        namespace=deployment.metadata.namespace,
        creation_timestamp=deployment.metadata.creation_timestamp,
        labels=deployment.metadata.labels,
        annotations=filter_annotations_by_key_pattern(
            deployment.metadata.annotations, annotation_key_pattern
        ),
        selector=deployment.spec.selector,
        containers=_thin_containers(deployment.pods),
        cluster=cluster_name,
        kubernetes_cluster_hostname=kubernetes_cluster_hostname,
    )


def deployment_conditions(
    deployment_status: api.DeploymentStatus,
) -> section.DeploymentConditions | None:
    if not deployment_status.conditions:
        return None
    return section.DeploymentConditions(**deployment_status.conditions)


def controller_strategy(controller: Deployment | DaemonSet | StatefulSet) -> section.UpdateStrategy:
    return section.UpdateStrategy.parse_obj(controller.spec)


def controller_spec(controller: Deployment | DaemonSet | StatefulSet) -> section.ControllerSpec:
    return section.ControllerSpec(min_ready_seconds=controller.spec.min_ready_seconds)


def deployment_replicas(deployment: Deployment) -> section.DeploymentReplicas:
    return section.DeploymentReplicas(
        available=deployment.status.replicas.available,
        desired=deployment.status.replicas.replicas,
        ready=deployment.status.replicas.ready,
        updated=deployment.status.replicas.updated,
    )


def _thin_containers(pods: Collection[api.Pod]) -> section.ThinContainers:
    containers: list[api.ContainerStatus] = []
    for pod in pods:
        if container_map := pod.containers:
            containers.extend(container_map.values())
    return section.ThinContainers(
        images=frozenset(container.image for container in containers),
        names=[api.ContainerName(container.name) for container in containers],
    )


@dataclass(frozen=True)
class DaemonSet(PodOwner):
    metadata: api.MetaData
    spec: api.DaemonSetSpec
    status: api.DaemonSetStatus
    type_: str = "daemonset"


def daemonset_replicas(
    daemonset: DaemonSet,
) -> section.DaemonSetReplicas:
    return section.DaemonSetReplicas(
        available=daemonset.status.number_available,
        desired=daemonset.status.desired_number_scheduled,
        updated=daemonset.status.updated_number_scheduled,
        misscheduled=daemonset.status.number_misscheduled,
        ready=daemonset.status.number_ready,
    )


def daemonset_info(
    daemonset: DaemonSet,
    cluster_name: str,
    kubernetes_cluster_hostname: str,
    annotation_key_pattern: AnnotationOption,
) -> section.DaemonSetInfo:
    return section.DaemonSetInfo(
        name=daemonset.metadata.name,
        namespace=daemonset.metadata.namespace,
        creation_timestamp=daemonset.metadata.creation_timestamp,
        labels=daemonset.metadata.labels,
        annotations=filter_annotations_by_key_pattern(
            daemonset.metadata.annotations, annotation_key_pattern
        ),
        selector=daemonset.spec.selector,
        containers=_thin_containers(daemonset.pods),
        cluster=cluster_name,
        kubernetes_cluster_hostname=kubernetes_cluster_hostname,
    )


@dataclass(frozen=True)
class StatefulSet(PodOwner):
    metadata: api.MetaData
    spec: api.StatefulSetSpec
    status: api.StatefulSetStatus
    type_: str = "statefulset"


def statefulset_replicas(statefulset: StatefulSet) -> section.StatefulSetReplicas:
    return section.StatefulSetReplicas(
        desired=statefulset.spec.replicas,
        ready=statefulset.status.ready_replicas,
        updated=statefulset.status.updated_replicas,
        available=statefulset.status.available_replicas,
    )


def statefulset_info(
    statefulset: StatefulSet,
    cluster_name: str,
    kubernetes_cluster_hostname: str,
    annotation_key_pattern: AnnotationOption,
) -> section.StatefulSetInfo:
    return section.StatefulSetInfo(
        name=statefulset.metadata.name,
        namespace=statefulset.metadata.namespace,
        creation_timestamp=statefulset.metadata.creation_timestamp,
        labels=statefulset.metadata.labels,
        annotations=filter_annotations_by_key_pattern(
            statefulset.metadata.annotations, annotation_key_pattern
        ),
        selector=statefulset.spec.selector,
        containers=_thin_containers(statefulset.pods),
        cluster=cluster_name,
        kubernetes_cluster_hostname=kubernetes_cluster_hostname,
    )


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
        return _pod_resources_from_api_pods(self.aggregation_pods)

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
        return _collect_memory_resources_from_api_pods(self.aggregation_pods)

    def cpu_resources(self) -> section.Resources:
        return _collect_cpu_resources_from_api_pods(self.aggregation_pods)

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


def _node_collector_daemons(daemonsets: Iterable[api.DaemonSet]) -> section.CollectorDaemons:
    # Extract DaemonSets with label key `node-collector`
    collector_daemons = defaultdict(list)
    for daemonset in daemonsets:
        if (label := daemonset.metadata.labels.get(api.LabelName("node-collector"))) is not None:
            collector_type = label.value
            collector_daemons[collector_type].append(daemonset.status)
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


PB_KUBE_OBJECT = (
    Cluster | api.CronJob | Deployment | DaemonSet | api.Namespace | Node | api.Pod | StatefulSet
)
PiggybackFormatter = Callable[[PB_KUBE_OBJECT], str]


@dataclass(frozen=True)
class ComposedEntities:
    # TODO: Currently, this class prepares APIData by packaging data from
    # different API queries. Some, but not all user configurations are taken
    # into account. In particular, some things such as namespace filtering is
    # done elsewhere. If we such functionality here, we can consider changing
    # the name to MonitoredEntities.
    daemonsets: Sequence[DaemonSet]
    statefulsets: Sequence[StatefulSet]
    deployments: Sequence[Deployment]
    nodes: Sequence[Node]
    cluster: Cluster

    @classmethod
    def from_api_resources(
        cls, excluded_node_roles: Sequence[str], api_data: APIData
    ) -> ComposedEntities:
        """Creating and filling the Cluster with the Kubernetes Objects"""

        LOGGER.debug("Constructing k8s objects based on collected API data")

        uid_to_api_pod = {api_pod.uid: api_pod for api_pod in api_data.pods}
        agent_deployments = [
            Deployment(
                metadata=api_deployment.metadata,
                spec=api_deployment.spec,
                status=api_deployment.status,
                pods=[uid_to_api_pod[uid] for uid in api_deployment.pods],
            )
            for api_deployment in api_data.deployments
        ]

        agent_daemonsets = [
            DaemonSet(
                metadata=api_daemon_set.metadata,
                spec=api_daemon_set.spec,
                status=api_daemon_set.status,
                pods=[uid_to_api_pod[uid] for uid in api_daemon_set.pods],
            )
            for api_daemon_set in api_data.daemonsets
        ]

        agent_statefulsets = [
            StatefulSet(
                metadata=api_statefulset.metadata,
                spec=api_statefulset.spec,
                status=api_statefulset.status,
                pods=[uid_to_api_pod[uid] for uid in api_statefulset.pods],
            )
            for api_statefulset in api_data.statefulsets
        ]

        node_to_api_pod = defaultdict(list)
        for api_pod in api_data.pods:
            if (node_name := api_pod.spec.node) is not None:
                node_to_api_pod[node_name].append(api_pod)

        agent_nodes = [
            Node(
                metadata=node_api.metadata,
                status=node_api.status,
                kubelet_health=node_api.kubelet_health,
                pods=node_to_api_pod[node_api.metadata.name],
            )
            for node_api in api_data.nodes
        ]

        agent_cluster = Cluster.from_api_resources(excluded_node_roles, api_data)

        LOGGER.debug(
            "Cluster composition: Nodes (%s), Deployments (%s), DaemonSets (%s), StatefulSets (%s)",
            len(agent_nodes),
            len(agent_deployments),
            len(agent_daemonsets),
            len(agent_statefulsets),
        )

        return cls(
            daemonsets=agent_daemonsets,
            statefulsets=agent_statefulsets,
            deployments=agent_deployments,
            nodes=agent_nodes,
            cluster=agent_cluster,
        )


# Namespace & Resource Quota specific


def namespace_info(
    namespace: api.Namespace,
    cluster_name: str,
    annotation_key_pattern: AnnotationOption,
    kubernetes_cluster_hostname: str,
) -> section.NamespaceInfo:
    return section.NamespaceInfo(
        name=namespace_name(namespace),
        creation_timestamp=namespace.metadata.creation_timestamp,
        labels=namespace.metadata.labels,
        annotations=filter_annotations_by_key_pattern(
            namespace.metadata.annotations, annotation_key_pattern
        ),
        cluster=cluster_name,
        kubernetes_cluster_hostname=kubernetes_cluster_hostname,
    )


def cron_job_info(
    cron_job: api.CronJob,
    cluster_name: str,
    kubernetes_cluster_hostname: str,
    annotation_key_pattern: AnnotationOption,
) -> section.CronJobInfo:
    return section.CronJobInfo(
        name=cron_job.metadata.name,
        namespace=cron_job.metadata.namespace,
        creation_timestamp=cron_job.metadata.creation_timestamp,
        labels=cron_job.metadata.labels,
        annotations=filter_annotations_by_key_pattern(
            cron_job.metadata.annotations, annotation_key_pattern
        ),
        schedule=cron_job.spec.schedule,
        concurrency_policy=cron_job.spec.concurrency_policy,
        failed_jobs_history_limit=cron_job.spec.failed_jobs_history_limit,
        successful_jobs_history_limit=cron_job.spec.successful_jobs_history_limit,
        suspend=cron_job.spec.suspend,
        cluster=cluster_name,
        kubernetes_cluster_hostname=kubernetes_cluster_hostname,
    )


def cron_job_status(
    status: api.CronJobStatus,
    timestamp_sorted_jobs: Sequence[api.Job],
) -> section.CronJobStatus:
    return section.CronJobStatus(
        active_jobs_count=len(status.active) if status.active else None,
        last_duration=_calculate_job_duration(last_completed_job)
        if (last_completed_job := _retrieve_last_completed_job(timestamp_sorted_jobs)) is not None
        else None,
        last_successful_time=status.last_successful_time,
        last_schedule_time=status.last_schedule_time,
    )


def _retrieve_last_completed_job(jobs: Sequence[api.Job]) -> api.Job | None:
    for job in jobs:
        if job.status.completion_time is not None:
            return job
    return None


def _calculate_job_duration(job: api.Job) -> float | None:
    if job.status.completion_time is None or job.status.start_time is None:
        return None

    return job.status.completion_time - job.status.start_time


def cron_job_latest_job(
    job: api.Job, pods: Mapping[api.PodUID, api.Pod]
) -> section.CronJobLatestJob:
    return section.CronJobLatestJob(
        status=section.JobStatus(
            conditions=job.status.conditions or [],
            start_time=job.status.start_time,
            completion_time=job.status.completion_time,
        ),
        pods=[
            section.JobPod(
                init_containers=pod.init_containers,
                containers=pod.containers,
                lifecycle=pod_lifecycle_phase(pod.status),
            )
            for pod_uid in job.pod_uids
            if (pod := pods.get(pod_uid)) is not None
        ],
    )


def filter_matching_namespace_resource_quota(
    namespace: api.NamespaceName, resource_quotas: Sequence[api.ResourceQuota]
) -> api.ResourceQuota | None:
    for resource_quota in resource_quotas:
        if resource_quota.metadata.namespace == namespace:
            return resource_quota
    return None


def filter_pods_by_resource_quota_criteria(
    pods: Sequence[api.Pod], resource_quota: api.ResourceQuota
) -> Sequence[api.Pod]:
    resource_quota_pods = filter_pods_by_resource_quota_scopes(
        pods, resource_quota.spec.scopes or ()
    )
    return filter_pods_by_resource_quota_scope_selector(
        resource_quota_pods, resource_quota.spec.scope_selector
    )


def filter_pods_by_resource_quota_scope_selector(
    pods: Sequence[api.Pod], scope_selector: api.ScopeSelector | None
) -> Sequence[api.Pod]:
    if scope_selector is None:
        return pods

    return [
        pod
        for pod in pods
        if all(
            _matches_scope_selector_match_expression(pod, match_expression)
            for match_expression in scope_selector.match_expressions
        )
    ]


def _matches_scope_selector_match_expression(
    pod: api.Pod, match_expression: api.ScopedResourceMatchExpression
) -> bool:
    # TODO: add support for CrossNamespacePodAffinity
    if match_expression.scope_name in [
        api.QuotaScope.BestEffort,
        api.QuotaScope.NotBestEffort,
        api.QuotaScope.Terminating,
        api.QuotaScope.NotTerminating,
    ]:
        return _matches_quota_scope(pod, match_expression.scope_name)

    if match_expression.scope_name != api.QuotaScope.PriorityClass:
        raise NotImplementedError(
            f"The resource quota scope name {match_expression.scope_name} "
            "is currently not supported"
        )

    # XNOR case for priority class
    # if the pod has a priority class and the operator is Exists then the pod is included
    # if the pod has no priority class and the operator is DoesNotExist then the pod is included
    if match_expression.operator in (api.ScopeOperator.Exists, api.ScopeOperator.DoesNotExist):
        return not (
            (pod.spec.priority_class_name is not None)
            ^ (match_expression.operator == api.ScopeOperator.Exists)
        )

    # XNOR case for priority class value
    # if operator is In and the priority class value is in the list of values then the pod is
    # included
    # if operator is NotIn and the priority class value is not in the list of values then the pod
    # is included
    if match_expression.operator in (api.ScopeOperator.In, api.ScopeOperator.NotIn):
        return not (
            (pod.spec.priority_class_name in match_expression.values)
            ^ (match_expression.operator == api.ScopeOperator.In)
        )

    raise NotImplementedError("Unsupported match expression operator")


def filter_pods_by_resource_quota_scopes(
    api_pods: Sequence[api.Pod], scopes: Sequence[api.QuotaScope] = ()
) -> Sequence[api.Pod]:
    """Filter pods based on selected scopes"""
    return [pod for pod in api_pods if all(_matches_quota_scope(pod, scope) for scope in scopes)]


def _matches_quota_scope(pod: api.Pod, scope: api.QuotaScope) -> bool:
    """Verifies if the pod scopes matches the scope criteria

    Reminder:
    * the Quota scope is rather ResourceQuota specific rather than Pod specific
    * the Quota scope encompasses multiple Pod concepts (see api.Pod model)
    * a Pod can have all multiple scopes (e.g PrioritClass, Terminating and BestEffort)
    """

    def pod_terminating_scope(
        pod: api.Pod,
    ) -> api.QuotaScope:
        return (
            api.QuotaScope.Terminating
            if (pod.spec.active_deadline_seconds is not None)
            else api.QuotaScope.NotTerminating
        )

    def pod_effort_scope(
        pod: api.Pod,
    ) -> api.QuotaScope:
        # TODO: change qos_class from Literal to Enum
        return (
            api.QuotaScope.BestEffort
            if (pod.status.qos_class == "besteffort")
            else api.QuotaScope.NotBestEffort
        )

    if scope == api.QuotaScope.PriorityClass:
        return pod.spec.priority_class_name is not None

    if scope in [api.QuotaScope.Terminating, api.QuotaScope.NotTerminating]:
        return pod_terminating_scope(pod) == scope

    if scope in [api.QuotaScope.BestEffort, api.QuotaScope.NotBestEffort]:
        return pod_effort_scope(pod) == scope

    raise NotImplementedError(f"Unsupported quota scope {scope}")


def pod_attached_persistent_volume_claim_names(pod: api.Pod) -> Iterator[str]:
    if (volumes := pod.spec.volumes) is None:
        return

    for volume in volumes:
        if volume.persistent_volume_claim is None:
            continue

        yield volume.persistent_volume_claim.claim_name


def attached_pvc_names_from_pods(pods: Sequence[api.Pod]) -> Sequence[str]:
    return list(
        {pvc_name for pod in pods for pvc_name in pod_attached_persistent_volume_claim_names(pod)}
    )


def filter_kubelet_volume_metrics(
    kubelet_metrics: Sequence[api.OpenMetricSample],
) -> Iterator[api.KubeletVolumeMetricSample]:
    yield from (m for m in kubelet_metrics if isinstance(m, api.KubeletVolumeMetricSample))


def serialize_attached_volumes_from_kubelet_metrics(
    volume_metric_samples: Iterator[api.KubeletVolumeMetricSample],
) -> Iterator[section.AttachedVolume]:
    """Serialize attached volumes from kubelet metrics

    A PV can be bound to one PVC only, so while a PV itself has no namespace, the PVC
    namespace + name can be used to identify it uniquely (and easily)

    Remember: since a PVC has a namespace, only the namespace + name combination is unique
    """

    def pvc_unique(v: api.KubeletVolumeMetricSample) -> tuple[str, str]:
        return v.labels.namespace, v.labels.persistentvolumeclaim

    for (namespace, pvc), samples in itertools.groupby(
        sorted(volume_metric_samples, key=pvc_unique), key=pvc_unique
    ):
        volume_details = {sample.metric_name.value: sample.value for sample in samples}
        yield section.AttachedVolume(
            capacity=volume_details["kubelet_volume_stats_capacity_bytes"],
            free=volume_details["kubelet_volume_stats_available_bytes"],
            persistent_volume_claim=pvc,
            namespace=NamespaceName(namespace),
        )


def group_serialized_volumes_by_namespace(
    serialized_pvs: Iterator[section.AttachedVolume],
) -> Mapping[NamespaceName, Mapping[str, section.AttachedVolume]]:
    namespaced_grouped_pvs: dict[NamespaceName, dict[str, section.AttachedVolume]] = {}
    for pv in serialized_pvs:
        namespace_pvs: dict[str, section.AttachedVolume] = namespaced_grouped_pvs.setdefault(
            pv.namespace, {}
        )
        namespace_pvs[pv.persistent_volume_claim] = pv
    return namespaced_grouped_pvs


def group_parsed_pvcs_by_namespace(
    api_pvcs: Sequence[api.PersistentVolumeClaim],
) -> Mapping[NamespaceName, Mapping[str, section.PersistentVolumeClaim]]:
    namespace_sorted_pvcs: dict[NamespaceName, dict[str, section.PersistentVolumeClaim]] = {}
    for pvc in api_pvcs:
        namespace_pvcs: dict[str, section.PersistentVolumeClaim] = namespace_sorted_pvcs.setdefault(
            pvc.metadata.namespace, {}
        )
        namespace_pvcs[pvc.metadata.name] = section.PersistentVolumeClaim(
            metadata=section.PersistentVolumeClaimMetaData.parse_obj(pvc.metadata),
            status=section.PersistentVolumeClaimStatus.parse_obj(pvc.status),
            volume_name=pvc.spec.volume_name,
        )
    return namespace_sorted_pvcs


def create_pvc_sections(
    piggyback_name: str,
    attached_pvc_names: Sequence[str],
    api_pvcs: Mapping[str, section.PersistentVolumeClaim],
    api_pvs: Mapping[str, section.PersistentVolume],
    attached_volumes: Mapping[str, section.AttachedVolume],
) -> Iterator[WriteableSection]:
    """Create PVC & PV related sections"""
    if not attached_pvc_names:
        return

    attached_pvcs = {pvc_name: api_pvcs[pvc_name] for pvc_name in attached_pvc_names}

    yield WriteableSection(
        piggyback_name=piggyback_name,
        section_name=SectionName("kube_pvc_v1"),
        section=section.PersistentVolumeClaims(claims=attached_pvcs),
    )

    pvc_attached_api_pvs = {
        pvc.volume_name: api_pvs[pvc.volume_name]
        for pvc in attached_pvcs.values()
        if pvc.volume_name is not None
    }

    if pvc_attached_api_pvs:
        yield WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_pvc_pvs_v1"),
            section=section.AttachedPersistentVolumes(volumes=pvc_attached_api_pvs),
        )

    pvc_attached_volumes = {
        pvc_name: volume
        for pvc_name in attached_pvc_names
        if (volume := attached_volumes.get(pvc_name)) is not None
    }
    if pvc_attached_volumes:
        yield WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_pvc_volumes_v1"),
            section=section.PersistentVolumeClaimAttachedVolumes(volumes=pvc_attached_volumes),
        )


# Pod specific helpers


def _collect_memory_resources_from_api_pods(pods: Sequence[api.Pod]) -> section.Resources:
    return aggregate_resources("memory", [c for pod in pods for c in pod.spec.containers])


def _collect_cpu_resources_from_api_pods(pods: Sequence[api.Pod]) -> section.Resources:
    return aggregate_resources("cpu", [c for pod in pods for c in pod.spec.containers])


def _pod_resources_from_api_pods(pods: Sequence[api.Pod]) -> section.PodResources:
    resources: defaultdict[str, list[str]] = defaultdict(list)
    for pod in pods:
        resources[pod.status.phase].append(pod_name(pod))
    return section.PodResources(**resources)


def pod_name(pod: api.Pod, prepend_namespace: bool = False) -> str:
    if not prepend_namespace:
        return pod.metadata.name

    return f"{pod.metadata.namespace}_{pod.metadata.name}"


def filter_pods_by_namespace(
    pods: Sequence[api.Pod], namespace: api.NamespaceName
) -> Sequence[api.Pod]:
    return [pod for pod in pods if pod_namespace(pod) == namespace]


def filter_pods_by_cron_job(pods: Sequence[api.Pod], cron_job: api.CronJob) -> Sequence[api.Pod]:
    return [pod for pod in pods if pod.uid in cron_job.pod_uids]


def filter_pods_by_phase(pods: Iterable[api.Pod], phase: api.Phase) -> Sequence[api.Pod]:
    return [pod for pod in pods if pod.status.phase == phase]


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


def pod_namespace(pod: api.Pod) -> api.NamespaceName:
    return pod.metadata.namespace


def namespace_name(namespace: api.Namespace) -> api.NamespaceName:
    """The name of the namespace
    Examples:
        >>> metadata = api.NamespaceMetaData.parse_obj({"name": "foo", "creation_timestamp": "2021-05-04T09:01:13Z", "labels": {}, "annotations": {}})
        >>> namespace = api.Namespace(metadata=metadata)
        >>> namespace_name(namespace)
        'foo'
    """
    return namespace.metadata.name


def kube_object_namespace_name(kube_object: KubeNamespacedObj) -> NamespaceName:
    """The namespace name of the Kubernetes object"""
    return kube_object.metadata.namespace


def cron_job_namespaced_name(cron_job: api.CronJob) -> str:
    """The name of the cron job appended to the namespace
    >>> metadata = api.MetaData.parse_obj({"name": "foo", "namespace": "bar", "creation_timestamp": "2021-05-04T09:01:13Z", "labels": {}, "annotations": {}})
    >>> cron_job_namespaced_name(api.CronJob(uid="cron_job_uid", job_uids=[], metadata=metadata, pod_uids=[], spec=api.CronJobSpec(concurrency_policy=api.ConcurrencyPolicy.Forbid, schedule="0 0 0 0 0", suspend=False, successful_jobs_history_limit=0, failed_jobs_history_limit=0), status=api.CronJobStatus(active=None, last_schedule_time=None, last_successful_time=None)))
    'bar_foo'
    """
    return f"{cron_job.metadata.namespace}_{cron_job.metadata.name}"


def controller_namespaced_name(controller: api.Controller) -> str:
    return f"{controller.namespace}_{controller.name}"


def _write_sections(sections: Mapping[str, Callable[[], section.Section | None]]) -> None:
    for section_name, section_call in sections.items():
        if section_output := section_call():
            with SectionWriter(section_name) as writer:
                writer.append(section_output.json())


def write_cluster_api_sections(cluster_name: str, cluster: Cluster) -> None:
    sections = {
        "kube_pod_resources_v1": cluster.pod_resources,
        "kube_allocatable_pods_v1": cluster.allocatable_pods,
        "kube_node_count_v1": cluster.node_count,
        "kube_cluster_details_v1": lambda: section.ClusterDetails.parse_obj(
            cluster.cluster_details
        ),
        "kube_memory_resources_v1": cluster.memory_resources,
        "kube_cpu_resources_v1": cluster.cpu_resources,
        "kube_allocatable_memory_resource_v1": cluster.allocatable_memory_resource,
        "kube_allocatable_cpu_resource_v1": cluster.allocatable_cpu_resource,
        "kube_cluster_info_v1": lambda: section.ClusterInfo(
            name=cluster_name, version=cluster.version()
        ),
        "kube_collector_daemons_v1": cluster.node_collector_daemons,
    }
    _write_sections(sections)


def write_cronjobs_api_sections(
    api_cron_jobs: Sequence[api.CronJob],
    api_cron_job_pods: Sequence[api.Pod],
    api_jobs: Mapping[api.JobUID, api.Job],
    host_settings: CheckmkHostSettings,
    piggyback_formatter: PiggybackFormatter,
) -> None:
    def output_cronjob_sections(
        cron_job: api.CronJob,
        cron_job_pods: Sequence[api.Pod],
    ) -> None:
        jobs = [api_jobs[uid] for uid in cron_job.job_uids]
        timestamp_sorted_jobs = sorted(jobs, key=lambda job: job.metadata.creation_timestamp)
        sections = {
            "kube_cron_job_info_v1": lambda: cron_job_info(
                cron_job,
                host_settings.cluster_name,
                host_settings.kubernetes_cluster_hostname,
                host_settings.annotation_key_pattern,
            ),
            "kube_cron_job_status_v1": lambda: cron_job_status(
                cron_job.status, timestamp_sorted_jobs
            ),
            "kube_cron_job_latest_job_v1": lambda: cron_job_latest_job(
                timestamp_sorted_jobs[-1], {pod.uid: pod for pod in cron_job_pods}
            )
            if len(timestamp_sorted_jobs) > 0
            else None,
            "kube_pod_resources_v1": lambda: _pod_resources_from_api_pods(cron_job_pods),
            "kube_memory_resources_v1": lambda: _collect_memory_resources_from_api_pods(
                cron_job_pods
            ),
            "kube_cpu_resources_v1": lambda: _collect_cpu_resources_from_api_pods(cron_job_pods),
        }
        _write_sections(sections)

    for api_cron_job in api_cron_jobs:
        with ConditionalPiggybackSection(piggyback_formatter(api_cron_job)):
            output_cronjob_sections(
                api_cron_job,
                filter_pods_by_cron_job(api_cron_job_pods, api_cron_job),
            )


def create_namespace_api_sections(
    api_namespace: api.Namespace,
    namespace_api_pods: Sequence[api.Pod],
    host_settings: CheckmkHostSettings,
    piggyback_name: str,
) -> Iterator[WriteableSection]:
    yield from (
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_namespace_info_v1"),
            section=namespace_info(
                api_namespace,
                host_settings.cluster_name,
                host_settings.annotation_key_pattern,
                host_settings.kubernetes_cluster_hostname,
            ),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_pod_resources_v1"),
            section=_pod_resources_from_api_pods(namespace_api_pods),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_memory_resources_v1"),
            section=_collect_memory_resources_from_api_pods(namespace_api_pods),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_cpu_resources_v1"),
            section=_collect_cpu_resources_from_api_pods(namespace_api_pods),
        ),
    )


def create_resource_quota_api_sections(
    resource_quota: api.ResourceQuota, piggyback_name: str
) -> Iterator[WriteableSection]:
    if (hard := resource_quota.spec.hard) is None:
        return

    if hard.memory is not None:
        yield WriteableSection(
            section_name=SectionName("kube_resource_quota_memory_resources_v1"),
            section=section.HardResourceRequirement.parse_obj(hard.memory),
            piggyback_name=piggyback_name,
        )

    if hard.cpu is not None:
        yield WriteableSection(
            section_name=SectionName("kube_resource_quota_cpu_resources_v1"),
            section=section.HardResourceRequirement.parse_obj(hard.cpu),
            piggyback_name=piggyback_name,
        )


def write_nodes_api_sections(
    api_nodes: Sequence[Node],
    host_settings: CheckmkHostSettings,
    piggyback_formatter: PiggybackFormatter,
) -> None:
    def output_sections(cluster_node: Node) -> None:
        sections = {
            "kube_node_container_count_v1": cluster_node.container_count,
            "kube_node_kubelet_v1": cluster_node.kubelet,
            "kube_pod_resources_v1": cluster_node.pod_resources,
            "kube_allocatable_pods_v1": cluster_node.allocatable_pods,
            "kube_node_info_v1": lambda: cluster_node.info(
                host_settings.cluster_name,
                host_settings.kubernetes_cluster_hostname,
                host_settings.annotation_key_pattern,
            ),
            "kube_cpu_resources_v1": cluster_node.cpu_resources,
            "kube_memory_resources_v1": cluster_node.memory_resources,
            "kube_allocatable_cpu_resource_v1": cluster_node.allocatable_cpu_resource,
            "kube_allocatable_memory_resource_v1": cluster_node.allocatable_memory_resource,
            "kube_node_conditions_v1": cluster_node.conditions,
            "kube_node_custom_conditions_v1": cluster_node.custom_conditions,
        }
        _write_sections(sections)

    for node in api_nodes:
        with ConditionalPiggybackSection(piggyback_formatter(node)):
            output_sections(node)


def create_deployment_api_sections(
    api_deployment: Deployment, host_settings: CheckmkHostSettings, piggyback_name: str
) -> Iterator[WriteableSection]:
    yield from (
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_deployment_info_v1"),
            section=deployment_info(
                api_deployment,
                host_settings.cluster_name,
                host_settings.kubernetes_cluster_hostname,
                host_settings.annotation_key_pattern,
            ),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_pod_resources_v1"),
            section=api_deployment.pod_resources(),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_memory_resources_v1"),
            section=api_deployment.memory_resources(),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_cpu_resources_v1"),
            section=api_deployment.cpu_resources(),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_update_strategy_v1"),
            section=controller_strategy(api_deployment),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_controller_spec_v1"),
            section=controller_spec(api_deployment),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_deployment_replicas_v1"),
            section=deployment_replicas(api_deployment),
        ),
    )

    if (section_conditions := deployment_conditions(api_deployment.status)) is not None:
        yield WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_deployment_conditions_v1"),
            section=section_conditions,
        )


def namespaced_name_from_metadata(metadata: api.MetaData) -> str:
    return api.namespaced_name(metadata.namespace, metadata.name)


def create_daemon_set_api_sections(
    api_daemonset: DaemonSet, host_settings: CheckmkHostSettings, piggyback_name: str
) -> Iterator[WriteableSection]:
    yield from (
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_pod_resources_v1"),
            section=api_daemonset.pod_resources(),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_memory_resources_v1"),
            section=api_daemonset.memory_resources(),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_cpu_resources_v1"),
            section=api_daemonset.cpu_resources(),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_daemonset_info_v1"),
            section=daemonset_info(
                api_daemonset,
                host_settings.cluster_name,
                host_settings.kubernetes_cluster_hostname,
                host_settings.annotation_key_pattern,
            ),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_update_strategy_v1"),
            section=controller_strategy(api_daemonset),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_daemonset_replicas_v1"),
            section=daemonset_replicas(api_daemonset),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_controller_spec_v1"),
            section=controller_spec(api_daemonset),
        ),
    )


def create_statefulset_api_sections(
    api_statefulset: StatefulSet,
    host_settings: CheckmkHostSettings,
    piggyback_name: str,
) -> Iterator[WriteableSection]:
    yield from (
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_pod_resources_v1"),
            section=api_statefulset.pod_resources(),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_memory_resources_v1"),
            section=api_statefulset.memory_resources(),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_cpu_resources_v1"),
            section=api_statefulset.cpu_resources(),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_statefulset_info_v1"),
            section=statefulset_info(
                api_statefulset,
                host_settings.cluster_name,
                host_settings.kubernetes_cluster_hostname,
                host_settings.annotation_key_pattern,
            ),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_update_strategy_v1"),
            section=controller_strategy(api_statefulset),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_controller_spec_v1"),
            section=controller_spec(api_statefulset),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_statefulset_replicas_v1"),
            section=statefulset_replicas(api_statefulset),
        ),
    )


def write_machine_sections(
    composed_entities: ComposedEntities,
    machine_sections: Mapping[str, str],
    piggyback_formatter: PiggybackFormatter,
) -> None:
    # make sure we only print sections for nodes currently visible via Kubernetes api:
    for node in composed_entities.nodes:
        if sections := machine_sections.get(str(node.metadata.name)):
            with ConditionalPiggybackSection(piggyback_formatter(node)):
                sys.stdout.write(sections)


def _supported_cluster_collector_major_version(
    collector_version: str, supported_max_major_version: int
) -> bool:
    """Check if the collector version is supported

    Examples:
         >>> _supported_cluster_collector_major_version('1.1.2', 1)
         True

         >>> _supported_cluster_collector_major_version('2.2.1b2', 0)
         False
    """
    return int(collector_version[0]) <= supported_max_major_version


class ClusterConnectionError(Exception):
    pass


Model = TypeVar("Model")


def _parse_raw_metrics(content: bytes) -> list[RawMetrics]:
    return parse_raw_as(list[RawMetrics], content)


def request_cluster_collector(
    path: query.CollectorPath,
    config: query.CollectorSessionConfig,
    parser: Callable[[bytes], Model],
) -> Model:
    session = query.create_session(config, LOGGER)
    url = config.cluster_collector_endpoint + path
    request = requests.Request("GET", url)
    prepare_request = session.prepare_request(request)
    try:
        cluster_resp = session.send(
            prepare_request, verify=config.usage_verify_cert, timeout=config.requests_timeout()
        )
        cluster_resp.raise_for_status()
    except requests.HTTPError as e:
        raise CollectorHandlingException(
            title="Connection Error",
            detail=f"Failed attempting to communicate with cluster collector at URL {url}",
        ) from e
    except requests.exceptions.RequestException as e:
        # All TCP Exceptions raised by requests inherit from RequestException,
        # see https://docs.python-requests.org/en/latest/user/quickstart/#errors-and-exceptions
        raise CollectorHandlingException(
            title="Setup Error",
            detail=f"Failure to establish a connection to cluster collector at URL {url}",
        ) from e

    return parser(cluster_resp.content)


def pod_lookup_from_api_pod(api_pod: api.Pod) -> PodLookupName:
    return lookup_name(pod_namespace(api_pod), pod_name(api_pod))


KubeNamespacedObj = TypeVar(
    "KubeNamespacedObj", bound=DaemonSet | Deployment | StatefulSet | api.CronJob | api.Pod
)


def kube_objects_from_namespaces(
    kube_objects: Sequence[KubeNamespacedObj], namespaces: set[api.NamespaceName]
) -> Sequence[KubeNamespacedObj]:
    return [kube_obj for kube_obj in kube_objects if kube_obj.metadata.namespace in namespaces]


def namespaces_from_namespacenames(
    api_namespaces: Sequence[api.Namespace], namespace_names: set[api.NamespaceName]
) -> Sequence[api.Namespace]:
    return [
        api_namespace
        for api_namespace in api_namespaces
        if namespace_name(api_namespace) in namespace_names
    ]


def filter_monitored_namespaces(
    cluster_namespaces: set[api.NamespaceName],
    namespace_include_patterns: Sequence[str],
    namespace_exclude_patterns: Sequence[str],
) -> set[api.NamespaceName]:
    """Filter Kubernetes namespaces based on the provided patterns

    Examples:
        >>> filter_monitored_namespaces({api.NamespaceName("foo"), api.NamespaceName("bar")}, ["foo"], [])
        {'foo'}

        >>> filter_monitored_namespaces({api.NamespaceName("foo"), api.NamespaceName("bar")}, [], ["foo"])
        {'bar'}

        >>> sorted(filter_monitored_namespaces({api.NamespaceName("foo"), api.NamespaceName("bar"),
        ... api.NamespaceName("man")}, ["foo", "bar"], []))
        ['bar', 'foo']

    """
    if namespace_include_patterns:
        LOGGER.debug("Filtering for included namespaces")
        return _filter_namespaces(cluster_namespaces, namespace_include_patterns)

    if namespace_exclude_patterns:
        LOGGER.debug("Filtering for namespaces based on excluded patterns")
        return cluster_namespaces - _filter_namespaces(
            cluster_namespaces, namespace_exclude_patterns
        )

    return cluster_namespaces


def _filter_namespaces(
    kubernetes_namespaces: set[api.NamespaceName], re_patterns: Sequence[str]
) -> set[api.NamespaceName]:
    """Filter namespaces based on the provided regular expression patterns

    Examples:
         >>> sorted(_filter_namespaces({api.NamespaceName("foo"), api.NamespaceName("bar"),
         ... api.NamespaceName("man")}, ["foo", "man"]))
         ['foo', 'man']
    """
    return {
        namespace
        for namespace in kubernetes_namespaces
        if any_match_from_list_of_infix_patterns(re_patterns, namespace)
    }


def _names_of_running_pods(
    kube_object: Node | Deployment | DaemonSet | StatefulSet,
) -> Sequence[PodLookupName]:
    # TODO: This function should really be simple enough to allow a doctest.
    # However, due to the way kube_object classes are constructed (e.g., see
    # api_to_agent_daemonset) this is currently not possible. If we improve
    # this function to use a PodOwner method instead, we can side-step these
    # issues.
    running_pods = filter_pods_by_phase(kube_object.pods, api.Phase.RUNNING)
    return list(map(pod_lookup_from_api_pod, running_pods))


def determine_pods_to_host(
    monitored_objects: Sequence[MonitoredObject],
    composed_entities: ComposedEntities,
    monitored_namespaces: set[api.NamespaceName],
    api_pods: Sequence[api.Pod],
    resource_quotas: Sequence[api.ResourceQuota],
    monitored_api_namespaces: Sequence[api.Namespace],
    api_cron_jobs: Sequence[api.CronJob],
    piggyback_formatter: PiggybackFormatter,
) -> PodsToHost:
    piggybacks: list[Piggyback] = []
    namespace_piggies = []
    if MonitoredObject.namespaces in monitored_objects:
        for api_namespace in monitored_api_namespaces:
            namespace_api_pods = filter_pods_by_phase(
                filter_pods_by_namespace(api_pods, namespace_name(api_namespace)),
                api.Phase.RUNNING,
            )
            resource_quota = filter_matching_namespace_resource_quota(
                namespace_name(api_namespace), resource_quotas
            )
            if resource_quota is not None:
                resource_quota_pod_names = [
                    pod_lookup_from_api_pod(pod)
                    for pod in filter_pods_by_resource_quota_criteria(
                        namespace_api_pods, resource_quota
                    )
                ]
            else:
                resource_quota_pod_names = []

            piggyback_name = piggyback_formatter(api_namespace)
            piggybacks.append(
                Piggyback(
                    piggyback=piggyback_name,
                    pod_names=[pod_lookup_from_api_pod(pod) for pod in namespace_api_pods],
                )
            )
            namespace_piggies.append(
                Piggyback(
                    piggyback=piggyback_name,
                    pod_names=resource_quota_pod_names,
                )
            )
    # TODO: write_object_sections_based_on_performance_pods is the equivalent
    # function based solely on api.Pod rather than class Pod. All objects relying
    # on write_sections_based_on_performance_pods should be refactored to use the
    # other function similar to namespaces
    if MonitoredObject.pods in monitored_objects:
        monitored_pods = kube_objects_from_namespaces(
            filter_pods_by_phase(api_pods, api.Phase.RUNNING),
            monitored_namespaces,
        )
        if MonitoredObject.cronjobs_pods not in monitored_objects:
            cronjob_pod_uids = {uid for cronjob in api_cron_jobs for uid in cronjob.pod_uids}
            monitored_pods = [pod for pod in monitored_pods if pod.uid not in cronjob_pod_uids]
        piggybacks.extend(
            Piggyback(
                piggyback=piggyback_formatter(pod),
                pod_names=[pod_lookup_from_api_pod(pod)],
            )
            for pod in monitored_pods
        )
    if MonitoredObject.nodes in monitored_objects:
        piggybacks.extend(
            Piggyback(
                piggyback=piggyback_formatter(node),
                pod_names=names,
            )
            for node in composed_entities.nodes
            if (names := _names_of_running_pods(node))
        )
    name_type_objects: Sequence[
        tuple[str, MonitoredObject, Sequence[Deployment | DaemonSet | StatefulSet]]
    ] = [
        ("deployment", MonitoredObject.deployments, composed_entities.deployments),
        ("statefulset", MonitoredObject.statefulsets, composed_entities.statefulsets),
        ("daemonset", MonitoredObject.daemonsets, composed_entities.daemonsets),
    ]
    for _object_type_name, object_type, objects in name_type_objects:
        if object_type in monitored_objects:
            piggybacks.extend(
                Piggyback(
                    piggyback=piggyback_formatter(k),
                    pod_names=names,
                )
                for k in kube_objects_from_namespaces(objects, monitored_namespaces)
                if (names := _names_of_running_pods(k))
            )
    piggybacks.append(
        Piggyback(
            piggyback="",
            pod_names=list(
                map(
                    pod_lookup_from_api_pod,
                    filter_pods_by_phase(
                        composed_entities.cluster.aggregation_pods, api.Phase.RUNNING
                    ),
                )
            ),
        )
    )
    if MonitoredObject.cronjobs in monitored_objects:
        piggybacks.extend(
            Piggyback(
                piggyback=piggyback_formatter(k),
                pod_names=[
                    pod_lookup_from_api_pod(pod)
                    for pod in filter_pods_by_phase(
                        filter_pods_by_cron_job(api_pods, k),
                        api.Phase.RUNNING,
                    )
                ],
            )
            for k in api_cron_jobs
        )
    return PodsToHost(
        piggybacks=piggybacks,
        namespace_piggies=namespace_piggies,
    )


def _identify_unsupported_node_collector_components(
    nodes: Sequence[section.NodeMetadata], supported_max_major_version: int
) -> Sequence[str]:
    invalid_nodes = []
    for node in nodes:
        unsupported_components = [
            f"{component.collector_type.value}: {component.checkmk_kube_agent.project_version}"
            for component in node.components.values()
            if not _supported_cluster_collector_major_version(
                component.checkmk_kube_agent.project_version,
                supported_max_major_version=supported_max_major_version,
            )
        ]
        if unsupported_components:
            invalid_nodes.append(f"{node.name} ({', '.join(unsupported_components)})")
    return invalid_nodes


def _group_metadata_by_node(
    node_collectors_metadata: Sequence[section.NodeCollectorMetadata],
) -> Sequence[section.NodeMetadata]:
    nodes_components: dict[section.NodeName, dict[str, section.NodeComponent]] = {}
    for node_collector in node_collectors_metadata:
        components = nodes_components.setdefault(node_collector.node, {})

        for component, version in node_collector.components.dict().items():
            if version is not None:
                components[component] = section.NodeComponent(
                    collector_type=node_collector.collector_type,
                    checkmk_kube_agent=node_collector.checkmk_kube_agent,
                    name=component,
                    version=version,
                )

    return [
        section.NodeMetadata(name=node_name, components=nodes_components[node_name])
        for node_name in {node_collector.node for node_collector in node_collectors_metadata}
    ]


def write_cluster_collector_info_section(
    processing_log: section.CollectorHandlerLog,
    cluster_collector: section.ClusterCollectorMetadata | None = None,
    node_collectors_metadata: Sequence[section.NodeMetadata] | None = None,
) -> None:
    with SectionWriter("kube_collector_metadata_v1") as writer:
        writer.append(
            section.CollectorComponentsMetadata(
                processing_log=processing_log,
                cluster_collector=cluster_collector,
                nodes=node_collectors_metadata,
            ).json()
        )


class CollectorHandlingException(Exception):
    # This exception is used as report medium for the Cluster Collector service
    def __init__(self, title: str, detail: str) -> None:
        self.title = title
        self.detail = detail
        super().__init__()

    def __str__(self) -> str:
        return f"{self.title}: {self.detail}" if self.detail else self.title


@contextlib.contextmanager
def collector_exception_handler(
    logs: list[section.CollectorHandlerLog], debug: bool = False
) -> Iterator:
    try:
        yield
    except CollectorHandlingException as e:
        if debug:
            raise e
        logs.append(
            section.CollectorHandlerLog(
                status=section.CollectorState.ERROR,
                title=e.title,
                detail=e.detail,
            )
        )


def pod_conditions(pod_status: api.PodStatus) -> section.PodConditions | None:
    if pod_status.conditions is None:
        return None

    return section.PodConditions(
        **{
            condition.type.value: section.PodCondition(
                status=condition.status,
                reason=condition.reason,
                detail=condition.detail,
                last_transition_time=condition.last_transition_time,
            )
            for condition in pod_status.conditions
            if condition.type is not None
        }
    )


def pod_container_specs(pod_spec: api.PodSpec) -> section.ContainerSpecs:
    return _pod_container_specs(pod_spec.containers)


def pod_init_container_specs(pod_spec: api.PodSpec) -> section.ContainerSpecs:
    return _pod_container_specs(pod_spec.init_containers)


def _pod_container_specs(container_specs: Sequence[api.ContainerSpec]) -> section.ContainerSpecs:
    return section.ContainerSpecs(
        containers={
            spec.name: section.ContainerSpec(image_pull_policy=spec.image_pull_policy)
            for spec in container_specs
        }
    )


def pod_start_time(pod_status: api.PodStatus) -> section.StartTime | None:
    if pod_status.start_time is None:
        return None

    return section.StartTime(start_time=pod_status.start_time)


def pod_lifecycle_phase(pod_status: api.PodStatus) -> section.PodLifeCycle:
    return section.PodLifeCycle(phase=pod_status.phase)


def pod_info(
    pod: api.Pod,
    cluster_name: str,
    kubernetes_cluster_hostname: str,
    annotation_key_pattern: AnnotationOption,
) -> section.PodInfo:
    return section.PodInfo(
        namespace=pod_namespace(pod),
        name=pod_name(pod),
        creation_timestamp=pod.metadata.creation_timestamp,
        labels=pod.metadata.labels,
        annotations=filter_annotations_by_key_pattern(
            pod.metadata.annotations, annotation_key_pattern
        ),
        node=pod.spec.node,
        host_network=pod.spec.host_network,
        dns_policy=pod.spec.dns_policy,
        host_ip=pod.status.host_ip,
        pod_ip=pod.status.pod_ip,
        qos_class=pod.status.qos_class,
        restart_policy=pod.spec.restart_policy,
        uid=pod.uid,
        controllers=[
            section.Controller(
                type_=c.type_,
                name=c.name,
            )
            for c in pod.controllers
        ],
        cluster=cluster_name,
        kubernetes_cluster_hostname=kubernetes_cluster_hostname,
    )


def create_pod_api_sections(
    pod: api.Pod,
    piggyback_name: str,
) -> Iterator[WriteableSection]:
    yield from (
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_pod_container_specs_v1"),
            section=pod_container_specs(pod.spec),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_pod_init_container_specs_v1"),
            section=pod_init_container_specs(pod.spec),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_pod_lifecycle_v1"),
            section=pod_lifecycle_phase(pod.status),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_cpu_resources_v1"),
            section=_collect_cpu_resources_from_api_pods([pod]),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_memory_resources_v1"),
            section=_collect_memory_resources_from_api_pods([pod]),
        ),
    )

    if (section_conditions := pod_conditions(pod.status)) is not None:
        yield WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_pod_conditions_v1"),
            section=section_conditions,
        )

    if (section_start_time := pod_start_time(pod.status)) is not None:
        yield WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_start_time_v1"),
            section=section_start_time,
        )

    if pod.containers:
        yield WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_pod_containers_v1"),
            section=section.PodContainers(containers=pod.containers),
        )

    if pod.init_containers:
        yield WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_pod_init_containers_v1"),
            section=section.PodContainers(containers=pod.init_containers),
        )


def cluster_piggyback_formatter(
    cluster_name: str, object_type: str, obj_namespaced_name: str
) -> str:
    return f"{object_type}_{cluster_name}_{obj_namespaced_name}"


def piggyback_formatter_with_cluster_name(
    cluster_name: str,
    kube_object: PB_KUBE_OBJECT,
) -> str:
    match kube_object:
        case Cluster():
            return ""
        case Node():
            return cluster_piggyback_formatter(
                cluster_name,
                object_type="node",
                obj_namespaced_name=kube_object.metadata.name,
            )
        case Deployment() | DaemonSet() | StatefulSet():
            return cluster_piggyback_formatter(
                cluster_name,
                object_type=kube_object.type_,
                obj_namespaced_name=namespaced_name_from_metadata(kube_object.metadata),
            )
        case api.Namespace():
            return cluster_piggyback_formatter(
                cluster_name,
                object_type="namespace",
                obj_namespaced_name=namespace_name(kube_object),
            )
        case api.CronJob():
            return cluster_piggyback_formatter(
                cluster_name,
                object_type="cronjob",
                obj_namespaced_name=namespaced_name_from_metadata(kube_object.metadata),
            )
        case api.Pod():
            return cluster_piggyback_formatter(
                cluster_name,
                object_type="pod",
                obj_namespaced_name=namespaced_name_from_metadata(kube_object.metadata),
            )


def main(args: list[str] | None = None) -> int:  # pylint: disable=too-many-branches
    if args is None:
        cmk.utils.password_store.replace_passwords()
        args = sys.argv[1:]
    arguments = parse_arguments(args)
    checkmk_host_settings = CheckmkHostSettings(
        cluster_name=arguments.cluster,
        kubernetes_cluster_hostname=arguments.kubernetes_cluster_hostname,
        annotation_key_pattern=arguments.annotation_key_pattern,
    )

    try:
        setup_logging(arguments.verbose)
        LOGGER.debug("parsed arguments: %s\n", arguments)

        with cmk.utils.profile.Profile(
            enabled=bool(arguments.profile), profile_file=arguments.profile
        ):
            client_config = query.parse_api_session_config(arguments)
            LOGGER.info("Collecting API data")
            try:
                api_data = from_kubernetes(
                    client_config,
                    LOGGER,
                    query_kubelet_endpoints=MonitoredObject.pvcs in arguments.monitored_objects,
                )
            except urllib3.exceptions.MaxRetryError as e:
                raise ClusterConnectionError(
                    f"Failed to establish a connection to {e.pool.host}:{e.pool.port} "
                    f"at URL {e.url}"
                ) from e
            except requests.RequestException as e:
                raise ClusterConnectionError(
                    f"Failed to establish a connection at URL {e.request.url} "
                ) from e

            # Namespaces are handled independently from the cluster object in order to improve
            # testability. The long term goal is to remove all objects from the cluster object
            composed_entities = ComposedEntities.from_api_resources(
                excluded_node_roles=arguments.roles or [], api_data=api_data
            )

            # Sections based on API server data
            LOGGER.info("Write cluster sections based on API data")
            write_cluster_api_sections(arguments.cluster, composed_entities.cluster)

            monitored_namespace_names = filter_monitored_namespaces(
                {namespace_name(namespace) for namespace in api_data.namespaces},
                arguments.namespace_include_patterns,
                arguments.namespace_exclude_patterns,
            )

            namespace_grouped_api_pvcs = group_parsed_pvcs_by_namespace(
                api_data.persistent_volume_claims
            )

            api_persistent_volumes = {
                pv.metadata.name: section.PersistentVolume(name=pv.metadata.name, spec=pv.spec)
                for pv in api_data.persistent_volumes
            }
            namespaced_grouped_attached_volumes = group_serialized_volumes_by_namespace(
                serialize_attached_volumes_from_kubelet_metrics(
                    filter_kubelet_volume_metrics(api_data.kubelet_open_metrics)
                )
            )
            piggyback_formatter = functools.partial(
                piggyback_formatter_with_cluster_name, arguments.cluster
            )

            if MonitoredObject.nodes in arguments.monitored_objects:
                LOGGER.info("Write nodes sections based on API data")
                write_nodes_api_sections(
                    composed_entities.nodes,
                    host_settings=checkmk_host_settings,
                    piggyback_formatter=piggyback_formatter,
                )

            if MonitoredObject.deployments in arguments.monitored_objects:
                LOGGER.info("Write deployments sections based on API data")
                for deployment in kube_objects_from_namespaces(
                    composed_entities.deployments, monitored_namespace_names
                ):
                    deployment_piggyback_name = piggyback_formatter(deployment)
                    sections = create_deployment_api_sections(
                        deployment,
                        host_settings=checkmk_host_settings,
                        piggyback_name=deployment_piggyback_name,
                    )
                    if MonitoredObject.pvcs in arguments.monitored_objects:
                        deployment_namespace = kube_object_namespace_name(deployment)
                        sections = chain(
                            sections,
                            create_pvc_sections(
                                piggyback_name=deployment_piggyback_name,
                                attached_pvc_names=attached_pvc_names_from_pods(deployment.pods),
                                api_pvcs=namespace_grouped_api_pvcs.get(deployment_namespace, {}),
                                api_pvs=api_persistent_volumes,
                                attached_volumes=namespaced_grouped_attached_volumes.get(
                                    deployment_namespace, {}
                                ),
                            ),
                        )
                    common.write_sections(sections)

            resource_quotas = api_data.resource_quotas
            # Namespaces are handled differently to other objects. Namespace piggyback hosts
            # should only be created if at least one running or pending pod is found in the
            # namespace.
            running_pending_pods = [
                pod
                for pod in api_data.pods
                if pod.status.phase in [api.Phase.RUNNING, api.Phase.PENDING]
            ]
            namespacenames_running_pending_pods = {
                pod_namespace(pod) for pod in running_pending_pods
            }
            monitored_api_namespaces = namespaces_from_namespacenames(
                api_data.namespaces,
                monitored_namespace_names.intersection(namespacenames_running_pending_pods),
            )
            if MonitoredObject.namespaces in arguments.monitored_objects:
                LOGGER.info("Write namespaces sections based on API data")
                for api_namespace in monitored_api_namespaces:
                    namespace_piggyback_name = piggyback_formatter(api_namespace)
                    api_pods_from_namespace = filter_pods_by_namespace(
                        api_data.pods, namespace_name(api_namespace)
                    )
                    namespace_sections = create_namespace_api_sections(
                        api_namespace,
                        api_pods_from_namespace,
                        host_settings=checkmk_host_settings,
                        piggyback_name=namespace_piggyback_name,
                    )
                    if (
                        api_resource_quota := filter_matching_namespace_resource_quota(
                            namespace_name(api_namespace), resource_quotas
                        )
                    ) is not None:
                        namespace_sections = chain(
                            namespace_sections,
                            create_resource_quota_api_sections(
                                api_resource_quota, piggyback_name=namespace_piggyback_name
                            ),
                        )
                    common.write_sections(namespace_sections)

            if MonitoredObject.daemonsets in arguments.monitored_objects:
                LOGGER.info("Write daemon sets sections based on API data")
                for daemonset in kube_objects_from_namespaces(
                    composed_entities.daemonsets, monitored_namespace_names
                ):
                    daemonset_piggyback_name = piggyback_formatter(daemonset)
                    daemonset_sections = create_daemon_set_api_sections(
                        daemonset,
                        host_settings=checkmk_host_settings,
                        piggyback_name=daemonset_piggyback_name,
                    )
                    if MonitoredObject.pvcs in arguments.monitored_objects:
                        daemonset_namespace = kube_object_namespace_name(daemonset)
                        daemonset_sections = chain(
                            daemonset_sections,
                            create_pvc_sections(
                                piggyback_name=daemonset_piggyback_name,
                                attached_pvc_names=attached_pvc_names_from_pods(daemonset.pods),
                                api_pvcs=namespace_grouped_api_pvcs.get(daemonset_namespace, {}),
                                api_pvs=api_persistent_volumes,
                                attached_volumes=namespaced_grouped_attached_volumes.get(
                                    daemonset_namespace, {}
                                ),
                            ),
                        )
                    common.write_sections(daemonset_sections)

            if MonitoredObject.statefulsets in arguments.monitored_objects:
                LOGGER.info("Write StatefulSets sections based on API data")
                for statefulset in kube_objects_from_namespaces(
                    composed_entities.statefulsets, monitored_namespace_names
                ):
                    statefulset_piggyback_name = piggyback_formatter(statefulset)
                    statefulset_sections = create_statefulset_api_sections(
                        statefulset,
                        host_settings=checkmk_host_settings,
                        piggyback_name=statefulset_piggyback_name,
                    )
                    if MonitoredObject.pvcs in arguments.monitored_objects:
                        statefulset_namespace = kube_object_namespace_name(statefulset)
                        statefulset_sections = chain(
                            statefulset_sections,
                            create_pvc_sections(
                                piggyback_name=statefulset_piggyback_name,
                                attached_pvc_names=attached_pvc_names_from_pods(statefulset.pods),
                                api_pvcs=namespace_grouped_api_pvcs.get(statefulset_namespace, {}),
                                api_pvs=api_persistent_volumes,
                                attached_volumes=namespaced_grouped_attached_volumes.get(
                                    statefulset_namespace, {}
                                ),
                            ),
                        )
                    common.write_sections(statefulset_sections)

            api_cron_job_pods = [
                api_pod
                for cron_job in api_data.cron_jobs
                for api_pod in api_data.pods
                if api_pod.uid in cron_job.pod_uids
            ]
            if MonitoredObject.cronjobs in arguments.monitored_objects:
                write_cronjobs_api_sections(
                    kube_objects_from_namespaces(api_data.cron_jobs, monitored_namespace_names),
                    api_cron_job_pods,
                    {job.uid: job for job in api_data.jobs},
                    host_settings=checkmk_host_settings,
                    piggyback_formatter=piggyback_formatter,
                )

            if MonitoredObject.pods in arguments.monitored_objects:
                LOGGER.info("Write pods sections based on API data")
                pods_in_relevant_namespaces = kube_objects_from_namespaces(
                    api_data.pods, monitored_namespace_names
                )
                if MonitoredObject.cronjobs_pods in arguments.monitored_objects:
                    monitored_pods = pods_in_relevant_namespaces
                else:
                    cronjob_pod_ids = {pod_lookup_from_api_pod(pod) for pod in api_cron_job_pods}
                    monitored_pods = [
                        pod
                        for pod in pods_in_relevant_namespaces
                        if pod_lookup_from_api_pod(pod) not in cronjob_pod_ids
                    ]

                for pod in monitored_pods:
                    pod_piggyback_name = piggyback_formatter(pod)
                    sections = create_pod_api_sections(pod, piggyback_name=pod_piggyback_name)
                    sections = chain(
                        sections,
                        [
                            WriteableSection(
                                piggyback_name=pod_piggyback_name,
                                section_name=SectionName("kube_pod_info_v1"),
                                section=pod_info(
                                    pod=pod,
                                    cluster_name=checkmk_host_settings.cluster_name,
                                    kubernetes_cluster_hostname=checkmk_host_settings.kubernetes_cluster_hostname,
                                    annotation_key_pattern=checkmk_host_settings.annotation_key_pattern,
                                ),
                            )
                        ],
                    )

                    if MonitoredObject.pvcs in arguments.monitored_objects:
                        sections = chain(
                            sections,
                            create_pvc_sections(
                                piggyback_name=pod_piggyback_name,
                                attached_pvc_names=list(
                                    pod_attached_persistent_volume_claim_names(pod)
                                ),
                                api_pvcs=namespace_grouped_api_pvcs.get(pod_namespace(pod), {}),
                                api_pvs=api_persistent_volumes,
                                attached_volumes=namespaced_grouped_attached_volumes.get(
                                    pod_namespace(pod), {}
                                ),
                            ),
                        )
                    common.write_sections(sections)

            usage_config = query.parse_session_config(arguments)

            # Skip machine & container sections when cluster agent endpoint not configured
            if isinstance(usage_config, query.NoUsageConfig):
                return 0

            if isinstance(usage_config, query.PrometheusSessionConfig):
                cpu, memory = query.send_requests(
                    usage_config,
                    [
                        query.Query.sum_rate_container_cpu_usage_seconds_total,
                        query.Query.sum_container_memory_working_set_bytes,
                    ],
                    logger=LOGGER,
                )

                common.write_sections(
                    [prometheus_section.debug_section(usage_config.query_url(), cpu, memory)]
                )
                prometheus_selectors = prometheus_section.create_selectors(cpu[1], memory[1])
                pods_to_host = determine_pods_to_host(
                    composed_entities=composed_entities,
                    monitored_objects=arguments.monitored_objects,
                    monitored_namespaces=monitored_namespace_names,
                    api_pods=api_data.pods,
                    resource_quotas=resource_quotas,
                    api_cron_jobs=api_data.cron_jobs,
                    monitored_api_namespaces=monitored_api_namespaces,
                    piggyback_formatter=piggyback_formatter,
                )
                common.write_sections(
                    common.create_sections(*prometheus_selectors, pods_to_host=pods_to_host)
                )
                write_machine_sections(
                    composed_entities,
                    machine_sections=prometheus_section.machine_sections(usage_config),
                    piggyback_formatter=piggyback_formatter,
                )
                return 0

            assert isinstance(usage_config, query.CollectorSessionConfig)

            # Sections based on cluster collector performance data

            # Handling of any of the cluster components should not crash the special agent as this
            # would discard all the API data. Special Agent failures of the Cluster Collector
            # components will not be highlighted in the usual Checkmk service but in a separate
            # service

            collector_metadata_logs: list[section.CollectorHandlerLog] = []
            with collector_exception_handler(logs=collector_metadata_logs, debug=arguments.debug):
                metadata = request_cluster_collector(
                    query.CollectorPath.metadata,
                    usage_config,
                    section.Metadata.parse_raw,
                )

                supported_collector_version = 1
                if not _supported_cluster_collector_major_version(
                    metadata.cluster_collector_metadata.checkmk_kube_agent.project_version,
                    supported_max_major_version=supported_collector_version,
                ):
                    raise CollectorHandlingException(
                        title="Version Error",
                        detail=f"Cluster Collector version {metadata.cluster_collector_metadata.checkmk_kube_agent.project_version} is not supported",
                    )

                nodes_metadata = _group_metadata_by_node(metadata.node_collector_metadata)

                if invalid_nodes := _identify_unsupported_node_collector_components(
                    nodes_metadata,
                    supported_max_major_version=supported_collector_version,
                ):
                    raise CollectorHandlingException(
                        title="Version Error",
                        detail=f"Following Nodes have unsupported components and should be "
                        f"downgraded: {', '.join(invalid_nodes)}",
                    )

                collector_metadata_logs.append(
                    section.CollectorHandlerLog(
                        status=section.CollectorState.OK,
                        title="Retrieved successfully",
                    )
                )

            try:
                write_cluster_collector_info_section(
                    processing_log=collector_metadata_logs[-1],
                    cluster_collector=metadata.cluster_collector_metadata,
                    node_collectors_metadata=nodes_metadata,
                )
            except UnboundLocalError:
                write_cluster_collector_info_section(processing_log=collector_metadata_logs[-1])
                return 0

            collector_container_logs: list[section.CollectorHandlerLog] = []
            with collector_exception_handler(logs=collector_container_logs, debug=arguments.debug):
                LOGGER.info("Collecting container metrics from cluster collector")
                container_metrics = request_cluster_collector(
                    query.CollectorPath.container_metrics,
                    usage_config,
                    performance.parse_performance_metrics,
                )

                if not container_metrics:
                    raise CollectorHandlingException(
                        title="No data",
                        detail="No container metrics were collected from the cluster collector",
                    )

                pods_to_host = determine_pods_to_host(
                    composed_entities=composed_entities,
                    monitored_objects=arguments.monitored_objects,
                    monitored_namespaces=monitored_namespace_names,
                    api_pods=api_data.pods,
                    resource_quotas=resource_quotas,
                    api_cron_jobs=api_data.cron_jobs,
                    monitored_api_namespaces=monitored_api_namespaces,
                    piggyback_formatter=piggyback_formatter,
                )
                try:
                    collector_selectors = performance.create_selectors(
                        cluster_name=arguments.cluster,
                        container_metrics=container_metrics,
                    )
                except Exception as e:
                    raise CollectorHandlingException(
                        title="Processing Error",
                        detail="Successfully queried and processed container metrics, but "
                        "an error occurred while processing the data",
                    ) from e

                try:
                    common.write_sections(
                        common.create_sections(*collector_selectors, pods_to_host=pods_to_host)
                    )

                except Exception as e:
                    raise CollectorHandlingException(
                        title="Sections write out Error",
                        detail="Metrics were successfully processed but Checkmk sections could not "
                        "be written out",
                    ) from e

                # Log when successfully queried and processed the metrics
                collector_container_logs.append(
                    section.CollectorHandlerLog(
                        status=section.CollectorState.OK,
                        title="Processed successfully",
                        detail="Successfully queried and processed container metrics",
                    )
                )

            # Sections based on cluster collector machine sections
            collector_machine_logs: list[section.CollectorHandlerLog] = []
            with collector_exception_handler(logs=collector_machine_logs, debug=arguments.debug):
                LOGGER.info("Collecting machine sections from cluster collector")
                machine_sections = request_cluster_collector(
                    query.CollectorPath.machine_sections,
                    usage_config,
                    _parse_raw_metrics,
                )

                if not machine_sections:
                    raise CollectorHandlingException(
                        title="No data",
                        detail="No machine sections were collected from the cluster collector",
                    )

                if MonitoredObject.nodes in arguments.monitored_objects:
                    try:
                        write_machine_sections(
                            composed_entities,
                            {s["node_name"]: s["sections"] for s in machine_sections},
                            piggyback_formatter,
                        )
                    except Exception as e:
                        raise CollectorHandlingException(
                            title="Sections write out Error",
                            detail="Metrics were successfully processed but Checkmk sections could "
                            "not be written out",
                        ) from e

                # Log when successfully queried and processed the metrics
                collector_machine_logs.append(
                    section.CollectorHandlerLog(
                        status=section.CollectorState.OK,
                        title="Processed successfully",
                        detail="Machine sections queried and processed successfully",
                    )
                )

            with SectionWriter("kube_collector_processing_logs_v1") as writer:
                writer.append(
                    section.CollectorProcessingLogs(
                        container=collector_container_logs[-1],
                        machine=collector_machine_logs[-1],
                    ).json()
                )
    except Exception as e:
        if arguments.debug:
            raise
        sys.stderr.write("%s" % e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
