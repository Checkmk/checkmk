#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Special agent for monitoring Kubernetes clusters. This agent is required for
monitoring data provided by the Kubernetes API and the Checkmk collectors,
which can optionally be deployed within a cluster. The agent requires
Kubernetes version v1.21 or higher. Moreover, read access to the Kubernetes API
endpoints monitored by Checkmk must be provided.
"""

# mypy: warn_return_any
# mypy: disallow_untyped_defs

from __future__ import annotations

import abc
import argparse
import collections
import contextlib
import enum
import functools
import json
import logging
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import (
    Any,
    Callable,
    Collection,
    Container,
    DefaultDict,
    Dict,
    Iterable,
    Iterator,
    List,
    Literal,
    Mapping,
    MutableMapping,
    NewType,
    Optional,
    Protocol,
    Sequence,
    Set,
    Tuple,
    TypeVar,
    Union,
)
from urllib.parse import urlparse

import requests
import urllib3
from kubernetes import client  # type: ignore[import]
from pydantic import BaseModel

import cmk.utils.password_store
import cmk.utils.paths
import cmk.utils.profile
from cmk.utils.http_proxy_config import deserialize_http_proxy_config, HTTPProxyConfig
from cmk.utils.misc import typeshed_issue_7724

from cmk.special_agents.utils import vcrtrace
from cmk.special_agents.utils.agent_common import ConditionalPiggybackSection, SectionWriter
from cmk.special_agents.utils.request_helper import get_requests_ca
from cmk.special_agents.utils_kubernetes.api_server import from_kubernetes
from cmk.special_agents.utils_kubernetes.schemata import api, section

LOGGER = logging.getLogger()

AGENT_TMP_PATH = Path(
    cmk.utils.paths.tmp_dir if os.environ.get("OMD_SITE") else tempfile.gettempdir(), "agent_kube"
)

SectionName = NewType("SectionName", str)
SectionJson = NewType("SectionJson", str)

NATIVE_NODE_CONDITION_TYPES = [
    "Ready",
    "MemoryPressure",
    "DiskPressure",
    "PIDPressure",
    "NetworkUnavailable",
]

RawMetrics = Mapping[str, str]

MetricName = NewType("MetricName", str)
ContainerName = NewType("ContainerName", str)
PodLookupName = NewType("PodLookupName", str)
PodNamespacedName = NewType("PodNamespacedName", str)


class PerformanceMetric(BaseModel):
    container_name: ContainerName
    name: MetricName
    value: float
    timestamp: float


class RateMetric(BaseModel):
    name: str
    rate: float


class PerformanceContainer(BaseModel):
    name: ContainerName
    pod_lookup_name: PodLookupName
    metrics: Mapping[MetricName, PerformanceMetric]
    rate_metrics: Optional[Mapping[MetricName, RateMetric]]


class PerformancePod(BaseModel):
    lookup_name: PodLookupName
    containers: List[PerformanceContainer]


class CounterMetric(BaseModel):
    name: MetricName
    value: float
    timestamp: float


class ContainerMetricsStore(BaseModel):
    name: ContainerName
    metrics: Mapping[MetricName, CounterMetric]


class ContainersStore(BaseModel):
    containers: Mapping[ContainerName, ContainerMetricsStore]


class ContainerMetadata(BaseModel):
    name: ContainerName
    pod_lookup_name: PodLookupName


class TCPTimeout(BaseModel):
    connect: int
    read: int


class PBFormatter(Protocol):
    def __call__(self, object_type: str, namespaced_name: str) -> str:
        ...


class ObjectSpecificPBFormatter(Protocol):
    def __call__(self, namespaced_name: str) -> str:
        ...


class AnnotationNonPatternOption(enum.Enum):
    ignore_all = "ignore_all"
    import_all = "import_all"


AnnotationOption = Union[
    Literal[AnnotationNonPatternOption.ignore_all, AnnotationNonPatternOption.import_all],
    str,
]


class MonitoredObject(enum.Enum):
    deployments = "deployments"
    daemonsets = "daemonsets"
    statefulsets = "statefulsets"
    namespaces = "namespaces"
    nodes = "nodes"
    pods = "pods"
    cronjobs_pods = "cronjobs_pods"


def parse_arguments(args: List[str]) -> argparse.Namespace:
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
    p.add_argument(
        "--cluster-collector-endpoint",
        help="Endpoint to query metrics from Kubernetes cluster agent",
    )
    p.add_argument(
        "--cluster-collector-proxy",
        type=str,
        default="FROM_ENVIRONMENT",
        metavar="PROXY",
        help=(
            "HTTP proxy used to connect to the Kubernetes cluster agent. If not set, the environment settings "
            "will be used."
        ),
    )

    p.add_argument("--verify-cert-api", action="store_true", help="Verify certificate")
    p.add_argument("--verify-cert-collector", action="store_true", help="Verify certificate")
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
        "--cluster-collector-connect-timeout",
        type=int,
        default=10,
        help="The timeout in seconds the special agent will wait for a "
        "connection to the cluster collector.",
    )
    p.add_argument(
        "--cluster-collector-read-timeout",
        type=int,
        default=12,
        help="The timeout in seconds the special agent will wait for a "
        "response from the cluster collector.",
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


class PodOwner(abc.ABC):
    def __init__(self, pods: Sequence[api.Pod]) -> None:
        self._pods: Sequence[api.Pod] = pods


class PodNamespacedOwner(PodOwner, abc.ABC):
    @property
    @abc.abstractmethod
    def namespace(self) -> Optional[api.NamespaceName]:
        raise NotImplementedError()


class Pod:
    def __init__(
        self,
        uid: api.PodUID,
        metadata: api.MetaData[str],
        status: api.PodStatus,
        spec: api.PodSpec,
        containers: Mapping[str, api.ContainerStatus],
        init_containers: Mapping[str, api.ContainerStatus],
        controllers: Sequence[api.Controller],
    ) -> None:
        self.uid = uid
        self.metadata = metadata
        self.spec = spec
        self.status = status
        self.containers = containers
        self.init_containers = init_containers
        self.controllers = controllers

    @property
    def phase(self) -> api.Phase:
        return self.status.phase

    @property
    def node(self) -> Optional[api.NodeName]:
        return self.spec.node

    def lifecycle_phase(self) -> section.PodLifeCycle:
        return section.PodLifeCycle(phase=self.phase)

    def name(self, prepend_namespace: bool = False) -> str:
        if not prepend_namespace:
            return self.metadata.name

        return f"{self.metadata.namespace}_{self.metadata.name}"

    # TODO: Extract this method in order to remove the double linking to the controller
    def info(
        self,
        cluster_name: str,
        kubernetes_cluster_hostname: str,
        annotation_key_pattern: AnnotationOption,
    ) -> section.PodInfo:
        return section.PodInfo(
            namespace=self.metadata.namespace,
            name=self.metadata.name,
            creation_timestamp=self.metadata.creation_timestamp,
            labels=self.metadata.labels,
            annotations=filter_annotations_by_key_pattern(
                self.metadata.annotations, annotation_key_pattern
            ),
            node=self.node,
            host_network=self.spec.host_network,
            dns_policy=self.spec.dns_policy,
            host_ip=self.status.host_ip,
            pod_ip=self.status.pod_ip,
            qos_class=self.status.qos_class,
            restart_policy=self.spec.restart_policy,
            uid=self.uid,
            controllers=[
                section.Controller(type_=controller.type_, name=controller.name)
                for controller in self.controllers
            ],
            cluster=cluster_name,
            kubernetes_cluster_hostname=kubernetes_cluster_hostname,
        )

    def conditions(self) -> Optional[section.PodConditions]:
        if not self.status.conditions:
            return None

        # TODO: separate section for custom conditions
        return section.PodConditions(
            **{
                condition.type.value: section.PodCondition(
                    status=condition.status,
                    reason=condition.reason,
                    detail=condition.detail,
                    last_transition_time=condition.last_transition_time,
                )
                for condition in self.status.conditions
                if condition.type is not None
            }
        )

    def container_statuses(self) -> Optional[section.PodContainers]:
        if not self.containers:
            return None
        return section.PodContainers(containers=self.containers)

    def init_container_statuses(self) -> Optional[section.PodContainers]:
        if not self.init_containers:
            return None
        return section.PodContainers(containers=self.init_containers)

    def container_specs(self) -> section.ContainerSpecs:
        return section.ContainerSpecs(
            containers={
                container_spec.name: section.ContainerSpec(
                    image_pull_policy=container_spec.image_pull_policy,
                )
                for container_spec in self.spec.containers
            }
        )

    def init_container_specs(self) -> section.ContainerSpecs:
        return section.ContainerSpecs(
            containers={
                container_spec.name: section.ContainerSpec(
                    image_pull_policy=container_spec.image_pull_policy,
                )
                for container_spec in self.spec.init_containers
            }
        )

    def start_time(self) -> section.StartTime | None:
        if self.status.start_time is None:
            return None
        return section.StartTime(start_time=self.status.start_time)


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
class Deployment(PodNamespacedOwner):
    def __init__(
        self,
        metadata: api.MetaData[str],
        spec: api.DeploymentSpec,
        status: api.DeploymentStatus,
        pods: Sequence[api.Pod],
    ) -> None:
        super().__init__(pods=pods)
        self.metadata = metadata
        self.spec = spec
        self.status = status
        self.type_: str = "deployment"

    @property
    def namespace(self) -> Optional[api.NamespaceName]:
        return self.metadata.namespace

    def name(self, prepend_namespace: bool = False) -> str:
        if not prepend_namespace:
            return self.metadata.name

        return f"{self.metadata.namespace}_{self.metadata.name}"

    def pods(self, phase: Optional[api.Phase] = None) -> Sequence[api.Pod]:
        if phase is None:
            return self._pods
        return [pod for pod in self._pods if pod.status.phase == phase]

    def info(
        self,
        cluster_name: str,
        kubernetes_cluster_hostname: str,
        annotation_key_pattern: AnnotationOption,
    ) -> section.DeploymentInfo:
        return section.DeploymentInfo(
            name=self.name(),
            namespace=self.metadata.namespace,
            creation_timestamp=self.metadata.creation_timestamp,
            labels=self.metadata.labels,
            annotations=filter_annotations_by_key_pattern(
                self.metadata.annotations, annotation_key_pattern
            ),
            selector=self.spec.selector,
            containers=_thin_containers(self.pods()),
            cluster=cluster_name,
            kubernetes_cluster_hostname=kubernetes_cluster_hostname,
        )

    def pod_resources(self) -> section.PodResources:
        return _pod_resources_from_api_pods(self._pods)

    def conditions(self) -> Optional[section.DeploymentConditions]:
        if not self.status.conditions:
            return None
        return section.DeploymentConditions(**self.status.conditions)

    def memory_resources(self) -> section.Resources:
        return _collect_memory_resources_from_api_pods(self._pods)

    def cpu_resources(self) -> section.Resources:
        return _collect_cpu_resources_from_api_pods(self._pods)

    def replicas(self) -> section.DeploymentReplicas:
        return section.DeploymentReplicas(
            desired=self.status.replicas.replicas,
            ready=self.status.replicas.ready,
            updated=self.status.replicas.updated,
        )

    def strategy(self) -> section.UpdateStrategy:
        return section.UpdateStrategy(strategy=self.spec.strategy)


def _thin_containers(pods: Collection[api.Pod]) -> section.ThinContainers:
    container_images = set()
    container_names = []
    for pod in pods:
        if containers := pod.containers:
            container_images.update({container.image for container in containers.values()})
            container_names.extend([container.name for container in containers.values()])
    return section.ThinContainers(images=container_images, names=container_names)


class DaemonSet(PodNamespacedOwner):
    def __init__(
        self,
        metadata: api.MetaData[str],
        spec: api.DaemonSetSpec,
        status: api.DaemonSetStatus,
        pods: Sequence[api.Pod],
    ) -> None:
        super().__init__(pods=pods)
        self.metadata = metadata
        self.spec = spec
        self._status = status
        self.type_: str = "daemonset"

    @property
    def namespace(self) -> Optional[api.NamespaceName]:
        return self.metadata.namespace

    def name(self, prepend_namespace: bool = False) -> str:
        if not prepend_namespace:
            return self.metadata.name

        return f"{self.metadata.namespace}_{self.metadata.name}"

    def pods(self, phase: Optional[api.Phase] = None) -> Sequence[api.Pod]:
        if phase is None:
            return self._pods
        return [pod for pod in self._pods if pod.status.phase == phase]

    def pod_resources(self) -> section.PodResources:
        return _pod_resources_from_api_pods(self._pods)

    def memory_resources(self) -> section.Resources:
        return _collect_memory_resources_from_api_pods(self._pods)

    def cpu_resources(self) -> section.Resources:
        return _collect_cpu_resources_from_api_pods(self._pods)

    def replicas(self) -> section.DaemonSetReplicas:
        return section.DaemonSetReplicas(
            desired=self._status.desired_number_scheduled,
            updated=self._status.updated_number_scheduled,
            misscheduled=self._status.number_misscheduled,
            ready=self._status.number_ready,
        )

    def strategy(self) -> section.UpdateStrategy:
        return section.UpdateStrategy(strategy=self.spec.strategy)


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
        containers=_thin_containers(daemonset.pods()),
        cluster=cluster_name,
        kubernetes_cluster_hostname=kubernetes_cluster_hostname,
    )


class StatefulSet(PodNamespacedOwner):
    def __init__(
        self,
        metadata: api.MetaData[str],
        spec: api.StatefulSetSpec,
        status: api.StatefulSetStatus,
        pods: Sequence[api.Pod],
    ) -> None:
        super().__init__(pods=pods)
        self.metadata = metadata
        self.spec = spec
        self._status = status
        self.type_: str = "statefulset"

    @property
    def namespace(self) -> Optional[api.NamespaceName]:
        return self.metadata.namespace

    def name(self, prepend_namespace: bool = False) -> str:
        if not prepend_namespace:
            return self.metadata.name
        return f"{self.metadata.namespace}_{self.metadata.name}"

    def pods(self, phase: Optional[api.Phase] = None) -> Sequence[api.Pod]:
        if phase is None:
            return self._pods
        return [pod for pod in self._pods if pod.status.phase == phase]

    def pod_resources(self) -> section.PodResources:
        return _pod_resources_from_api_pods(self._pods)

    def memory_resources(self) -> section.Resources:
        return _collect_memory_resources_from_api_pods(self._pods)

    def cpu_resources(self) -> section.Resources:
        return _collect_cpu_resources_from_api_pods(self._pods)

    def replicas(self) -> section.StatefulSetReplicas:
        return section.StatefulSetReplicas(
            desired=self.spec.replicas,
            ready=self._status.ready_replicas,
            updated=self._status.updated_replicas,
        )

    def strategy(self) -> section.UpdateStrategy:
        return section.UpdateStrategy(strategy=self.spec.strategy)


def statefulset_info(
    statefulset: StatefulSet,
    cluster_name: str,
    kubernetes_cluster_hostname: str,
    annotation_key_pattern: AnnotationOption,
) -> section.StatefulSetInfo:
    return section.StatefulSetInfo(
        name=statefulset.name(),
        namespace=statefulset.metadata.namespace,
        creation_timestamp=statefulset.metadata.creation_timestamp,
        labels=statefulset.metadata.labels,
        annotations=filter_annotations_by_key_pattern(
            statefulset.metadata.annotations, annotation_key_pattern
        ),
        selector=statefulset.spec.selector,
        containers=_thin_containers(statefulset.pods()),
        cluster=cluster_name,
        kubernetes_cluster_hostname=kubernetes_cluster_hostname,
    )


class Node(PodOwner):
    def __init__(
        self,
        metadata: api.MetaDataNoNamespace[api.NodeName],
        status: api.NodeStatus,
        resources: Dict[str, api.NodeResources],
        roles: Sequence[str],
        kubelet_info: api.KubeletInfo,
        pods: Sequence[api.Pod],
    ) -> None:
        super().__init__(pods=pods)
        self.metadata = metadata
        self.status = status
        self.resources = resources
        self.control_plane = "master" in roles or "control_plane" in roles
        self.roles = roles
        self.kubelet_info = kubelet_info

    @property
    def name(self) -> api.NodeName:
        return api.NodeName(self.metadata.name)

    def pods(self, phase: Optional[api.Phase] = None) -> Sequence[api.Pod]:
        if phase is None:
            return self._pods
        return [pod for pod in self._pods if pod.status.phase == phase]

    def pod_resources(self) -> section.PodResources:
        return _pod_resources_from_api_pods(self._pods)

    def memory_resources(self) -> section.Resources:
        return _collect_memory_resources_from_api_pods(self._pods)

    def cpu_resources(self) -> section.Resources:
        return _collect_cpu_resources_from_api_pods(self._pods)

    def allocatable_pods(self) -> section.AllocatablePods:
        return section.AllocatablePods(
            capacity=self.resources["capacity"].pods,
            allocatable=self.resources["allocatable"].pods,
        )

    def kubelet(self) -> section.KubeletInfo:
        return section.KubeletInfo.parse_obj(self.kubelet_info)

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
        type_count = collections.Counter(
            container.state.type.name for pod in self._pods for container in pod.containers.values()
        )
        return section.ContainerCount(**type_count)

    def allocatable_memory_resource(self) -> section.AllocatableResource:
        return section.AllocatableResource(
            context="node",
            value=self.resources["allocatable"].memory,
        )

    def allocatable_cpu_resource(self) -> section.AllocatableResource:
        return section.AllocatableResource(
            context="node",
            value=self.resources["allocatable"].cpu,
        )

    def conditions(self) -> Optional[section.NodeConditions]:
        if not self.status.conditions:
            return None

        return section.NodeConditions(
            **{
                condition.type_.lower(): section.NodeCondition(
                    status=condition.status,
                    reason=condition.reason,
                    detail=condition.detail,
                    last_transition_time=condition.last_transition_time,
                )
                for condition in self.status.conditions
                if condition.type_ in NATIVE_NODE_CONDITION_TYPES
            }
        )

    def custom_conditions(self) -> Optional[section.NodeCustomConditions]:
        if not self.status.conditions:
            return None

        return section.NodeCustomConditions(
            custom_conditions=[
                section.FalsyNodeCustomCondition(
                    type_=condition.type_,
                    status=condition.status,
                    reason=condition.reason,
                    detail=condition.detail,
                    last_transition_time=condition.last_transition_time,
                )
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


@dataclass
class Cluster:
    cluster_details: api.ClusterDetails
    excluded_node_roles: Sequence[str]
    daemonsets: Sequence[DaemonSet]
    statefulsets: Sequence[StatefulSet]
    deployments: Sequence[Deployment]
    pods: Mapping[api.PodUID, Pod]
    nodes: Sequence[Node]
    cluster_aggregation_pods: Sequence[api.Pod]
    cluster_aggregation_nodes: Sequence[Node]

    @classmethod
    def from_api_resources(
        cls,
        excluded_node_roles: Sequence[str],
        pods: Sequence[api.Pod],
        nodes: Sequence[api.Node],
        statefulsets: Sequence[api.StatefulSet],
        deployments: Sequence[api.Deployment],
        daemon_sets: Sequence[api.DaemonSet],
        cluster_details: api.ClusterDetails,
    ) -> Cluster:
        """Creating and filling the Cluster with the Kubernetes Objects"""

        LOGGER.debug("Constructing k8s objects based on collected API data")

        uid_to_api_pod = {api_pod.uid: api_pod for api_pod in pods}
        agent_deployments = [
            Deployment(
                api_deployment.metadata,
                api_deployment.spec,
                api_deployment.status,
                pods=[uid_to_api_pod[uid] for uid in api_deployment.pods],
            )
            for api_deployment in deployments
        ]

        agent_daemonsets = [
            DaemonSet(
                metadata=api_daemon_set.metadata,
                spec=api_daemon_set.spec,
                status=api_daemon_set.status,
                pods=[uid_to_api_pod[uid] for uid in api_daemon_set.pods],
            )
            for api_daemon_set in daemon_sets
        ]

        agent_statefulsets = [
            StatefulSet(
                metadata=api_statefulset.metadata,
                spec=api_statefulset.spec,
                status=api_statefulset.status,
                pods=[uid_to_api_pod[uid] for uid in api_statefulset.pods],
            )
            for api_statefulset in statefulsets
        ]

        agent_pods = {
            api_pod.uid: Pod(
                api_pod.uid,
                api_pod.metadata,
                api_pod.status,
                api_pod.spec,
                api_pod.containers,
                api_pod.init_containers,
                api_pod.controllers,
            )
            for api_pod in pods
        }

        node_to_api_pod = collections.defaultdict(list)
        for api_pod in pods:
            if (node_name := api_pod.spec.node) is not None:
                node_to_api_pod[node_name].append(api_pod)

        cluster_aggregation_nodes = []
        agent_nodes = []
        for node_api in nodes:
            node = Node(
                node_api.metadata,
                node_api.status,
                node_api.resources,
                node_api.roles,
                node_api.kubelet_info,
                pods=node_to_api_pod[node_api.metadata.name],
            )
            agent_nodes.append(node)
            if not any(
                any_match_from_list_of_infix_patterns(excluded_node_roles, role)
                for role in node_api.roles
            ):
                cluster_aggregation_nodes.append(node)

        cluster_aggregation_node_names = [node.name for node in cluster_aggregation_nodes]

        cluster_aggregation_pods = [
            pod
            for pod in pods
            if pod.spec.node in cluster_aggregation_node_names or pod.spec.node is None
        ]

        cluster = cls(
            cluster_details=cluster_details,
            excluded_node_roles=excluded_node_roles,
            deployments=agent_deployments,
            daemonsets=agent_daemonsets,
            statefulsets=agent_statefulsets,
            pods=agent_pods,
            nodes=agent_nodes,
            cluster_aggregation_nodes=cluster_aggregation_nodes,
            cluster_aggregation_pods=cluster_aggregation_pods,
        )
        LOGGER.debug(
            "Cluster composition: Nodes (%s), Deployments (%s), DaemonSets (%s), StatefulSets (%s), Pods (%s)",
            len(cluster.nodes),
            len(cluster.deployments),
            len(cluster.daemonsets),
            len(cluster.statefulsets),
            len(cluster.pods),
        )
        return cluster

    def pod_resources(self) -> section.PodResources:
        return _pod_resources_from_api_pods(self.cluster_aggregation_pods)

    def allocatable_pods(self) -> section.AllocatablePods:
        return section.AllocatablePods(
            capacity=sum(
                node.resources["capacity"].pods for node in self.cluster_aggregation_nodes
            ),
            allocatable=sum(
                node.resources["allocatable"].pods for node in self.cluster_aggregation_nodes
            ),
        )

    def namespaces(self) -> Set[api.NamespaceName]:
        namespaces: Set[api.NamespaceName] = set()
        namespaces.update(api.NamespaceName(pod.metadata.namespace) for pod in self.pods.values())
        return namespaces

    def node_count(self) -> section.NodeCount:
        node_count = section.NodeCount()
        for node in self.nodes:
            ready = (
                conditions := node.conditions()
            ) is not None and conditions.ready.status == api.NodeConditionStatus.TRUE
            if node.control_plane:
                if ready:
                    node_count.control_plane.ready += 1
                else:
                    node_count.control_plane.not_ready += 1
            else:
                if ready:
                    node_count.worker.ready += 1
                else:
                    node_count.worker.not_ready += 1
        return node_count

    def memory_resources(self) -> section.Resources:
        return _collect_memory_resources_from_api_pods(self.cluster_aggregation_pods)

    def cpu_resources(self) -> section.Resources:
        return _collect_cpu_resources_from_api_pods(self.cluster_aggregation_pods)

    def allocatable_memory_resource(self) -> section.AllocatableResource:
        return section.AllocatableResource(
            context="cluster",
            value=sum(
                node.resources["allocatable"].memory for node in self.cluster_aggregation_nodes
            ),
        )

    def allocatable_cpu_resource(self) -> section.AllocatableResource:
        return section.AllocatableResource(
            context="cluster",
            value=sum(node.resources["allocatable"].cpu for node in self.cluster_aggregation_nodes),
        )

    def version(self) -> api.GitVersion:
        return self.cluster_details.version

    def node_collector_daemons(self) -> section.CollectorDaemons:
        return _node_collector_daemons(self.daemonsets)


def _node_collector_daemons(daemonsets: Iterable[DaemonSet]) -> section.CollectorDaemons:
    # Extract DaemonSets with label key `node-collector`
    collector_daemons = collections.defaultdict(list)
    for daemonset in daemonsets:
        if (label := daemonset.metadata.labels.get(api.LabelName("node-collector"))) is not None:
            collector_type = label.value
            collector_daemons[collector_type].append(daemonset._status)
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
            conditions=job.status.conditions,
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
) -> Optional[api.ResourceQuota]:
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
    pods: Sequence[api.Pod], scope_selector: Optional[api.ScopeSelector]
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


# Pod specific helpers


def _collect_memory_resources(pods: Sequence[Pod]) -> section.Resources:
    return aggregate_resources("memory", [c for pod in pods for c in pod.spec.containers])


def _collect_memory_resources_from_api_pods(pods: Sequence[api.Pod]) -> section.Resources:
    return aggregate_resources("memory", [c for pod in pods for c in pod.spec.containers])


def _collect_cpu_resources(pods: Sequence[Pod]) -> section.Resources:
    return aggregate_resources("cpu", [c for pod in pods for c in pod.spec.containers])


def _collect_cpu_resources_from_api_pods(pods: Sequence[api.Pod]) -> section.Resources:
    return aggregate_resources("cpu", [c for pod in pods for c in pod.spec.containers])


def _pod_resources(pods: Collection[Pod]) -> section.PodResources:
    resources: DefaultDict[str, List[str]] = collections.defaultdict(list)
    for pod in pods:
        resources[pod.phase].append(pod.name())
    return section.PodResources(**resources)


def _pod_resources_from_api_pods(pods: Sequence[api.Pod]) -> section.PodResources:
    resources: DefaultDict[str, List[str]] = collections.defaultdict(list)
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
        >>> namespace_name(api.Namespace(metadata=api.MetaDataNoNamespace(name="foo", creation_timestamp=0.0, labels={}, annotations={})))
        'foo'
    """
    return namespace.metadata.name


def cron_job_namespaced_name(cron_job: api.CronJob) -> str:
    """The name of the cron job appended to the namespace
    >>> cron_job_namespaced_name(api.CronJob(uid="cron_job_uid", job_uids=[], metadata=api.MetaData(namespace="bar", name="foo", creation_timestamp=0.0, labels={}, annotations={}), pod_uids=[], spec=api.CronJobSpec(concurrency_policy=api.ConcurrencyPolicy.Forbid, schedule="0 0 0 0 0", suspend=False, successful_jobs_history_limit=0, failed_jobs_history_limit=0), status=api.CronJobStatus(active=None, last_schedule_time=None, last_successful_time=None)))
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
    cluster_name: str,
    annotation_key_pattern: AnnotationOption,
    api_cron_jobs: Sequence[api.CronJob],
    api_cron_job_pods: Sequence[api.Pod],
    api_jobs: Mapping[api.JobUID, api.Job],
    kubernetes_cluster_hostname: str,
    piggyback_formatter: ObjectSpecificPBFormatter,
) -> None:
    def output_cronjob_sections(
        cron_job: api.CronJob,
        cron_job_pods: Sequence[api.Pod],
    ) -> None:
        jobs = [api_jobs[uid] for uid in cron_job.job_uids]
        timestamp_sorted_jobs = sorted(jobs, key=lambda job: job.metadata.creation_timestamp)
        sections = {
            "kube_cron_job_info_v1": lambda: cron_job_info(
                cron_job, cluster_name, kubernetes_cluster_hostname, annotation_key_pattern
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
        with ConditionalPiggybackSection(
            piggyback_formatter(f"{api_cron_job.metadata.namespace}_{api_cron_job.metadata.name}")
        ):
            output_cronjob_sections(
                api_cron_job,
                filter_pods_by_cron_job(api_cron_job_pods, api_cron_job),
            )


def write_namespaces_api_sections(
    cluster_name: str,
    annotation_key_pattern: AnnotationOption,
    api_namespaces: Sequence[api.Namespace],
    api_resource_quotas: Sequence[api.ResourceQuota],
    api_pods: Sequence[api.Pod],
    kubernetes_cluster_hostname: str,
    piggyback_formatter: ObjectSpecificPBFormatter,
) -> None:
    def output_namespace_sections(
        namespace: api.Namespace, namespaced_api_pods: Sequence[api.Pod]
    ) -> None:
        sections = {
            "kube_namespace_info_v1": lambda: namespace_info(
                namespace,
                cluster_name,
                annotation_key_pattern,
                kubernetes_cluster_hostname,
            ),
            "kube_pod_resources_v1": lambda: _pod_resources_from_api_pods(namespaced_api_pods),
            "kube_memory_resources_v1": lambda: _collect_memory_resources_from_api_pods(
                namespaced_api_pods
            ),
            "kube_cpu_resources_v1": lambda: _collect_cpu_resources_from_api_pods(
                namespaced_api_pods
            ),
        }
        _write_sections(sections)

    def output_resource_quota_sections(resource_quota: api.ResourceQuota) -> None:
        sections = {
            "kube_resource_quota_memory_resources_v1": lambda: section.HardResourceRequirement.parse_obj(
                resource_quota.spec.hard.memory
            )
            if resource_quota.spec.hard
            else None,
            "kube_resource_quota_cpu_resources_v1": lambda: section.HardResourceRequirement.parse_obj(
                resource_quota.spec.hard.cpu
            )
            if resource_quota.spec.hard
            else None,
        }
        _write_sections(sections)

    for api_namespace in api_namespaces:
        with ConditionalPiggybackSection(piggyback_formatter(namespace_name(api_namespace))):
            output_namespace_sections(
                api_namespace, filter_pods_by_namespace(api_pods, namespace_name(api_namespace))
            )

            if (
                api_resource_quota := filter_matching_namespace_resource_quota(
                    namespace_name(api_namespace), api_resource_quotas
                )
            ) is not None:
                output_resource_quota_sections(api_resource_quota)


def write_nodes_api_sections(
    cluster_name: str,
    annotation_key_pattern: AnnotationOption,
    api_nodes: Sequence[Node],
    kubernetes_cluster_hostname: str,
    piggyback_formatter: ObjectSpecificPBFormatter,
) -> None:
    def output_sections(cluster_node: Node) -> None:
        sections = {
            "kube_node_container_count_v1": cluster_node.container_count,
            "kube_node_kubelet_v1": cluster_node.kubelet,
            "kube_pod_resources_v1": cluster_node.pod_resources,
            "kube_allocatable_pods_v1": cluster_node.allocatable_pods,
            "kube_node_info_v1": lambda: cluster_node.info(
                cluster_name,
                kubernetes_cluster_hostname,
                annotation_key_pattern,
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
        with ConditionalPiggybackSection(piggyback_formatter(node.name)):
            output_sections(node)


def write_deployments_api_sections(
    cluster_name: str,
    annotation_key_pattern: AnnotationOption,
    api_deployments: Sequence[Deployment],
    kubernetes_cluster_hostname: str,
    piggyback_formatter: ObjectSpecificPBFormatter,
) -> None:
    """Write the deployment relevant sections based on k8 API information"""

    def output_sections(cluster_deployment: Deployment) -> None:
        sections = {
            "kube_pod_resources_v1": cluster_deployment.pod_resources,
            "kube_memory_resources_v1": cluster_deployment.memory_resources,
            "kube_deployment_info_v1": lambda: cluster_deployment.info(
                cluster_name, kubernetes_cluster_hostname, annotation_key_pattern
            ),
            "kube_deployment_conditions_v1": cluster_deployment.conditions,
            "kube_cpu_resources_v1": cluster_deployment.cpu_resources,
            "kube_update_strategy_v1": cluster_deployment.strategy,
            "kube_deployment_replicas_v1": cluster_deployment.replicas,
        }
        _write_sections(sections)

    for deployment in api_deployments:
        with ConditionalPiggybackSection(
            piggyback_formatter(deployment.name(prepend_namespace=True))
        ):
            output_sections(deployment)


def write_daemon_sets_api_sections(
    cluster_name: str,
    annotation_key_pattern: AnnotationOption,
    api_daemon_sets: Sequence[DaemonSet],
    kubernetes_cluster_hostname: str,
    piggyback_formatter: ObjectSpecificPBFormatter,
) -> None:
    """Write the daemon set relevant sections based on k8 API information"""

    def output_sections(cluster_daemon_set: DaemonSet) -> None:
        sections = {
            "kube_pod_resources_v1": cluster_daemon_set.pod_resources,
            "kube_memory_resources_v1": cluster_daemon_set.memory_resources,
            "kube_cpu_resources_v1": cluster_daemon_set.cpu_resources,
            "kube_daemonset_info_v1": lambda: daemonset_info(
                cluster_daemon_set,
                cluster_name,
                kubernetes_cluster_hostname,
                annotation_key_pattern,
            ),
            "kube_update_strategy_v1": cluster_daemon_set.strategy,
            "kube_daemonset_replicas_v1": cluster_daemon_set.replicas,
        }
        _write_sections(sections)

    for daemon_set in api_daemon_sets:
        with ConditionalPiggybackSection(
            piggyback_formatter(daemon_set.name(prepend_namespace=True))
        ):
            output_sections(daemon_set)


def write_statefulsets_api_sections(
    cluster_name: str,
    annotation_key_pattern: AnnotationOption,
    api_statefulsets: Sequence[StatefulSet],
    kubernetes_cluster_hostname: str,
    piggyback_formatter: ObjectSpecificPBFormatter,
) -> None:
    """Write the StatefulSet relevant sections based on k8 API information"""

    def output_sections(cluster_statefulset: StatefulSet) -> None:
        sections = {
            "kube_pod_resources_v1": cluster_statefulset.pod_resources,
            "kube_memory_resources_v1": cluster_statefulset.memory_resources,
            "kube_cpu_resources_v1": cluster_statefulset.cpu_resources,
            "kube_statefulset_info_v1": lambda: statefulset_info(
                cluster_statefulset,
                cluster_name,
                kubernetes_cluster_hostname,
                annotation_key_pattern,
            ),
            "kube_update_strategy_v1": cluster_statefulset.strategy,
            "kube_statefulset_replicas_v1": cluster_statefulset.replicas,
        }
        _write_sections(sections)

    for statefulset in api_statefulsets:
        with ConditionalPiggybackSection(
            piggyback_formatter(statefulset.name(prepend_namespace=True))
        ):
            output_sections(statefulset)


def write_pods_api_sections(
    cluster_name: str,
    annotation_key_pattern: AnnotationOption,
    api_pods: Sequence[Pod],
    kubernetes_cluster_hostname: str,
    piggyback_formatter: ObjectSpecificPBFormatter,
) -> None:
    for pod in api_pods:
        with ConditionalPiggybackSection(piggyback_formatter(pod.name(prepend_namespace=True))):
            for section_name, section_content in pod_api_based_checkmk_sections(
                cluster_name, kubernetes_cluster_hostname, annotation_key_pattern, pod
            ):
                if section_content is None:
                    continue
                with SectionWriter(section_name) as writer:
                    writer.append(section_content.json())


def write_machine_sections(
    cluster: Cluster,
    machine_sections: Mapping[str, str],
    piggyback_formatter_node: ObjectSpecificPBFormatter,
) -> None:
    # make sure we only print sections for nodes currently visible via Kubernetes api:
    for node in cluster.nodes:
        if sections := machine_sections.get(str(node.name)):
            with ConditionalPiggybackSection(piggyback_formatter_node(node.name)):
                sys.stdout.write(sections)


def pod_api_based_checkmk_sections(
    cluster_name: str,
    kubernetes_cluster_hostname: str,
    annotation_key_pattern: AnnotationOption,
    pod: Pod,
) -> Iterable[tuple[str, section.Section | None]]:
    sections = (
        ("kube_pod_conditions_v1", pod.conditions),
        ("kube_pod_containers_v1", pod.container_statuses),
        ("kube_pod_container_specs_v1", pod.container_specs),
        ("kube_pod_init_containers_v1", pod.init_container_statuses),
        ("kube_pod_init_container_specs_v1", pod.init_container_specs),
        ("kube_start_time_v1", pod.start_time),
        ("kube_pod_lifecycle_v1", pod.lifecycle_phase),
        (
            "kube_pod_info_v1",
            lambda: pod.info(cluster_name, kubernetes_cluster_hostname, annotation_key_pattern),
        ),
        (
            "kube_cpu_resources_v1",
            lambda: _collect_cpu_resources([pod]),
        ),
        (
            "kube_memory_resources_v1",
            lambda: _collect_memory_resources([pod]),
        ),
    )
    for section_name, section_call in sections:
        yield section_name, section_call()


def filter_outdated_and_non_monitored_pods(
    performance_pods: Iterable[PerformancePod],
    lookup_name_to_piggyback_mappings: Container[PodLookupName],
) -> Sequence[PerformancePod]:
    """Filter out all performance data based pods that are not in the API data based lookup table

    Examples:
        >>> len(filter_outdated_and_non_monitored_pods(
        ... [PerformancePod(lookup_name=PodLookupName("foobar"), containers=[])],
        ... {PodLookupName("foobar")}))
        1

        >>> len(filter_outdated_and_non_monitored_pods(
        ... [PerformancePod(lookup_name=PodLookupName("foobar"), containers=[])],
        ... set()))
        0

    """
    LOGGER.info("Filtering out outdated and non-monitored pods from performance data")
    current_pods = []
    outdated_and_non_monitored_pods = []
    for performance_pod in performance_pods:
        if performance_pod.lookup_name in lookup_name_to_piggyback_mappings:
            current_pods.append(performance_pod)
            continue
        outdated_and_non_monitored_pods.append(performance_pod.lookup_name)

    LOGGER.debug(
        "Outdated or non-monitored performance pods: %s",
        ", ".join(outdated_and_non_monitored_pods),
    )
    return current_pods


def kube_object_performance_sections(
    performance_pods: Sequence[PerformancePod],
) -> List[Tuple[SectionName, SectionJson]]:
    performance_containers = [container for pod in performance_pods for container in pod.containers]
    return [
        (
            SectionName("kube_performance_memory_v1"),
            SectionJson(
                section.PerformanceUsage(
                    resource=section.Memory(
                        usage=_aggregate_metric(
                            performance_containers, MetricName("memory_working_set_bytes")
                        )
                    ),
                ).json()
            ),
        ),
        (
            SectionName("kube_performance_cpu_v1"),
            SectionJson(
                section.PerformanceUsage(
                    resource=section.Cpu(
                        usage=_aggregate_rate_metric(
                            performance_containers, MetricName("cpu_usage_seconds_total")
                        ),
                    ),
                ).json()
            ),
        ),
    ]


def resource_quota_performance_sections(
    resource_quota_performance_pods: Sequence[PerformancePod],
) -> List[Tuple[SectionName, SectionJson]]:
    if not resource_quota_performance_pods:
        return []

    performance_containers = [
        container for pod in resource_quota_performance_pods for container in pod.containers
    ]
    return [
        (
            SectionName("kube_resource_quota_performance_memory_v1"),
            SectionJson(
                section.PerformanceUsage(
                    resource=section.Memory(
                        usage=_aggregate_metric(
                            performance_containers, MetricName("memory_working_set_bytes")
                        )
                    ),
                ).json()
            ),
        ),
        (
            SectionName("kube_resource_quota_performance_cpu_v1"),
            SectionJson(
                section.PerformanceUsage(
                    resource=section.Cpu(
                        usage=_aggregate_rate_metric(
                            performance_containers, MetricName("cpu_usage_seconds_total")
                        ),
                    ),
                ).json()
            ),
        ),
    ]


def _aggregate_metric(
    containers: Collection[PerformanceContainer],
    metric: MetricName,
) -> float:
    """Aggregate a metric across all containers"""
    return 0.0 + sum(
        container.metrics[metric].value for container in containers if metric in container.metrics
    )


def _aggregate_rate_metric(
    containers: Collection[PerformanceContainer],
    rate_metric: MetricName,
) -> float:
    """Aggregate a rate metric across all containers"""
    return 0.0 + sum(
        container.rate_metrics[rate_metric].rate
        for container in containers
        if container.rate_metrics is not None and rate_metric in container.rate_metrics
    )


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


def request_cluster_collector(
    cluster_agent_url: str,
    token: str,
    verify: bool,
    timeout: TCPTimeout,
    proxy: HTTPProxyConfig,
) -> Any:
    if not verify:
        LOGGER.info("Disabling SSL certificate verification")
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    error_message = (
        f"Failed attempting to communicate with cluster collector at URL {cluster_agent_url}"
    )
    try:
        cluster_resp = requests.get(
            cluster_agent_url,
            headers={"Authorization": f"Bearer {token}"},
            verify=verify,
            timeout=(timeout.connect, timeout.read),
            proxies=typeshed_issue_7724(proxy.to_requests_proxies()),
        )
        cluster_resp.raise_for_status()
    except requests.HTTPError as e:
        raise CollectorHandlingException(
            title="Connection Error",
            detail=error_message,
        ) from e
    except requests.exceptions.RequestException as e:
        # All TCP Exceptions raised by requests inherit from RequestException,
        # see https://docs.python-requests.org/en/latest/user/quickstart/#errors-and-exceptions
        raise CollectorHandlingException(
            title="Setup Error",
            detail=f"Failure to establish a connection to cluster collector at URL {cluster_agent_url}",
        ) from e

    return json.loads(cluster_resp.content.decode("utf-8"))


def make_api_client(arguments: argparse.Namespace) -> client.ApiClient:
    config = client.Configuration()

    host = arguments.api_server_endpoint
    config.host = host
    if arguments.token:
        config.api_key_prefix["authorization"] = "Bearer"
        config.api_key["authorization"] = arguments.token

    http_proxy_config = deserialize_http_proxy_config(arguments.api_server_proxy)

    # Mimic requests.get("GET", url=host, proxies=http_proxy_config.to_requests_proxies())
    # function call, in order to obtain proxies in the same way as the requests library
    with requests.Session() as session:
        req = requests.models.Request(method="GET", url=host, data={}, params={})
        prep = session.prepare_request(req)
        proxies: MutableMapping = dict(http_proxy_config.to_requests_proxies() or {})
        proxies = session.merge_environment_settings(
            prep.url, proxies, session.stream, session.verify, session.cert
        )["proxies"]

    config.proxy = proxies.get(urlparse(host).scheme)
    config.proxy_headers = requests.adapters.HTTPAdapter().proxy_headers(config.proxy)

    if arguments.verify_cert_api:
        config.ssl_ca_cert = get_requests_ca()
    else:
        LOGGER.info("Disabling SSL certificate verification")
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        config.verify_ssl = False

    return client.ApiClient(config)


def parse_performance_metrics(
    cluster_collector_metrics: Sequence[RawMetrics],
) -> Sequence[PerformanceMetric]:
    metrics = []
    for metric in cluster_collector_metrics:
        metric_name = metric["metric_name"].replace("container_", "", 1)
        metrics.append(
            PerformanceMetric(
                container_name=ContainerName(metric["container_name"]),
                name=MetricName(metric_name),
                value=float(metric["metric_value_string"]),
                timestamp=float(metric["timestamp"]),
            )
        )
    return metrics


def filter_specific_metrics(
    metrics: Sequence[PerformanceMetric], metric_names: Sequence[MetricName]
) -> Iterator[PerformanceMetric]:
    for metric in metrics:
        if metric.name in metric_names:
            yield metric


def determine_rate_metrics(
    containers_counters: Mapping[ContainerName, ContainerMetricsStore],
    containers_counters_old: Mapping[ContainerName, ContainerMetricsStore],
) -> Mapping[ContainerName, Mapping[MetricName, RateMetric]]:
    """Determine the rate metrics for each container based on the current and previous
    counter metric values"""

    LOGGER.debug("Determine rate metrics from the latest containers counters stores")
    containers = {}
    for container in containers_counters.values():
        if (old_container := containers_counters_old.get(container.name)) is None:
            continue

        container_rate_metrics = container_available_rate_metrics(
            container.metrics, old_container.metrics
        )

        if not container_rate_metrics:
            continue

        containers[container.name] = container_rate_metrics
    return containers


def container_available_rate_metrics(
    counter_metrics: Mapping[MetricName, CounterMetric],
    old_counter_metrics: Mapping[MetricName, CounterMetric],
) -> Mapping[MetricName, RateMetric]:
    rate_metrics = {}
    for counter_metric in counter_metrics.values():
        if counter_metric.name not in old_counter_metrics:
            continue

        try:
            rate_value = calculate_rate(counter_metric, old_counter_metrics[counter_metric.name])
        except ZeroDivisionError:
            continue

        rate_metrics[counter_metric.name] = RateMetric(
            name=counter_metric.name,
            rate=rate_value,
        )
    return rate_metrics


def calculate_rate(counter_metric: CounterMetric, old_counter_metric: CounterMetric) -> float:
    """Calculate the rate value based on two counter metric values
    Examples:
        >>> calculate_rate(CounterMetric(name="foo", value=40, timestamp=60),
        ... CounterMetric(name="foo", value=10, timestamp=30))
        1.0
    """
    time_delta = counter_metric.timestamp - old_counter_metric.timestamp
    return (counter_metric.value - old_counter_metric.value) / time_delta


def load_containers_store(path: Path, file_name: str) -> ContainersStore:
    LOGGER.debug("Load previous cycle containers store from %s", file_name)
    try:
        with open(f"{path}/{file_name}", "r") as f:
            return ContainersStore(**json.loads(f.read()))
    except FileNotFoundError as e:
        LOGGER.info("Could not find metrics file. This is expected if the first run.")
        LOGGER.debug("Exception: %s", e)
    except SyntaxError:
        LOGGER.exception("Found metrics file, but could not parse it.")

    return ContainersStore(containers={})


def persist_containers_store(containers_store: ContainersStore, path: Path, file_name: str) -> None:
    file_path = f"{path}/{file_name}"
    LOGGER.debug("Creating directory %s for containers store file", path)
    path.mkdir(parents=True, exist_ok=True)
    LOGGER.debug("Persisting current containers store under %s", file_path)
    with open(file_path, "w") as f:
        f.write(containers_store.json())


def group_metrics_by_container(
    performance_metrics: Union[Iterator[PerformanceMetric], Sequence[PerformanceMetric]],
    omit_metrics: Sequence[MetricName] = (),
) -> Mapping[ContainerName, Mapping[MetricName, PerformanceMetric]]:
    containers: DefaultDict[
        ContainerName, Dict[MetricName, PerformanceMetric]
    ] = collections.defaultdict(dict)
    for performance_metric in performance_metrics:
        if performance_metric.name in omit_metrics:
            continue
        containers[performance_metric.container_name][performance_metric.name] = performance_metric
    return containers


def group_containers_by_pods(
    performance_containers: Iterator[PerformanceContainer],
) -> Mapping[PodLookupName, PerformancePod]:
    parsed_pods: Dict[PodLookupName, List[PerformanceContainer]] = {}
    for container in performance_containers:
        pod_containers = parsed_pods.setdefault(container.pod_lookup_name, [])
        pod_containers.append(container)

    return {
        pod_lookup_name: PerformancePod(lookup_name=pod_lookup_name, containers=containers)
        for pod_lookup_name, containers in parsed_pods.items()
    }


def parse_containers_metadata(
    metrics: Sequence[RawMetrics], lookup_func: Callable[[Mapping[str, str]], PodLookupName]
) -> Mapping[ContainerName, ContainerMetadata]:
    containers = {}
    for metric in metrics:
        if (container_name := metric["container_name"]) in containers:
            continue
        containers[ContainerName(container_name)] = ContainerMetadata(
            name=ContainerName(container_name), pod_lookup_name=lookup_func(metric)
        )
    return containers


def group_container_components(
    containers_metadata: Mapping[ContainerName, ContainerMetadata],
    containers_metrics: Mapping[ContainerName, Mapping[MetricName, PerformanceMetric]],
    containers_rate_metrics: Optional[
        Mapping[ContainerName, Mapping[MetricName, RateMetric]]
    ] = None,
) -> Iterator[PerformanceContainer]:
    if containers_rate_metrics is None:
        containers_rate_metrics = {}

    for container in containers_metadata.values():
        yield PerformanceContainer(
            name=container.name,
            pod_lookup_name=container.pod_lookup_name,
            metrics=containers_metrics[container.name],
            rate_metrics=containers_rate_metrics.get(container.name),
        )


def lookup_name(namespace: str, name: str) -> PodLookupName:
    """Parse the pod lookup name

    This function parses an identifier which is used to match the pod based on the
    performance data to the associating pod based on the Kubernetes API data

    The namespace & pod name combination is unique across the cluster and is used instead of the pod
    uid due to a cAdvisor bug. This bug causes it to return the container config hash value
    (kubernetes.io/config.hash) as the pod uid for system containers and consequently differs to the
    uid reported by the Kubernetes API.
    """
    return PodLookupName(f"{namespace}_{name}")


def pod_lookup_from_agent_pod(agent_pod: Pod) -> PodLookupName:
    return lookup_name(agent_pod.metadata.namespace, agent_pod.metadata.name)


def pod_lookup_from_api_pod(api_pod: api.Pod) -> PodLookupName:
    return lookup_name(pod_namespace(api_pod), pod_name(api_pod))


def pod_lookup_from_metric(metric: Mapping[str, str]) -> PodLookupName:
    return lookup_name(metric["namespace"], metric["pod_name"])


def pods_from_namespaces(
    pods: Iterable[api.Pod], namespaces: Set[api.NamespaceName]
) -> Sequence[api.Pod]:
    return [pod for pod in pods if pod.metadata.namespace in namespaces]


KubeNamespacedObj = TypeVar("KubeNamespacedObj", bound=Union[DaemonSet, Deployment, StatefulSet])


def kube_objects_from_namespaces(
    kube_objects: Sequence[KubeNamespacedObj], namespaces: Set[api.NamespaceName]
) -> Sequence[KubeNamespacedObj]:
    return [kube_obj for kube_obj in kube_objects if kube_obj.namespace in namespaces]


def namespaces_from_namespacenames(
    api_namespaces: Sequence[api.Namespace], namespace_names: Set[api.NamespaceName]
) -> Sequence[api.Namespace]:
    return [
        api_namespace
        for api_namespace in api_namespaces
        if namespace_name(api_namespace) in namespace_names
    ]


def filter_monitored_namespaces(
    cluster_namespaces: Set[api.NamespaceName],
    namespace_include_patterns: Sequence[str],
    namespace_exclude_patterns: Sequence[str],
) -> Set[api.NamespaceName]:
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
    kubernetes_namespaces: Set[api.NamespaceName], re_patterns: Sequence[str]
) -> Set[api.NamespaceName]:
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


def cluster_piggyback_formatter(cluster_name: str, object_type: str, namespaced_name: str) -> str:
    return f"{object_type}_{cluster_name}_{namespaced_name}"


def parse_and_group_containers_performance_metrics(
    cluster_name: str,
    container_metrics: Sequence[RawMetrics],
) -> Mapping[PodLookupName, PerformancePod]:
    """Parse container performance metrics and group them by pod"""

    performance_metrics = parse_performance_metrics(container_metrics)
    relevant_counter_metrics = [MetricName("cpu_usage_seconds_total")]
    performance_counter_metrics = filter_specific_metrics(
        performance_metrics, metric_names=relevant_counter_metrics
    )
    containers_counter_metrics = group_metrics_by_container(performance_counter_metrics)
    # We only persist the relevant counter metrics (not all metrics)
    current_cycle_store = ContainersStore(
        containers={
            container_name: ContainerMetricsStore(name=container_name, metrics=metrics)
            for container_name, metrics in containers_counter_metrics.items()
        }
    )
    store_file_name = f"{cluster_name}_containers_counters.json"
    previous_cycle_store = load_containers_store(
        path=AGENT_TMP_PATH,
        file_name=store_file_name,
    )
    containers_rate_metrics = determine_rate_metrics(
        current_cycle_store.containers, previous_cycle_store.containers
    )

    # The agent will store the latest counter values returned by the collector overwriting the
    # previous ones. The collector will return the same metric values for a certain time interval
    # while the values are not updated or outdated. This will result in no rate value if the agent
    # is polled too frequently (no performance section for the checks). All cases where no
    # performance section can be generated should be handled on the check side (reusing the same
    # value, etc.)
    persist_containers_store(current_cycle_store, path=AGENT_TMP_PATH, file_name=store_file_name)
    containers_metrics = group_metrics_by_container(
        performance_metrics, omit_metrics=relevant_counter_metrics
    )
    containers_metadata = parse_containers_metadata(container_metrics, pod_lookup_from_metric)
    performance_containers = group_container_components(
        containers_metadata, containers_metrics, containers_rate_metrics
    )

    performance_pods = group_containers_by_pods(performance_containers)
    return performance_pods


@dataclass
class Piggyback:
    piggyback: str
    pod_names: Sequence[PodLookupName]


@dataclass
class NamespacePiggy(Piggyback):
    resource_quota_pod_names: Sequence[PodLookupName]


@dataclass
class PodsToHost:
    piggybacks: Sequence[Piggyback]
    cluster_pods: Sequence[PodLookupName]
    namespace_piggies: Sequence[NamespacePiggy]


def _names_of_running_pods(
    kube_object: Union[Node, Deployment, DaemonSet, StatefulSet]
) -> Sequence[PodLookupName]:
    # TODO: This function should really be simple enough to allow a doctest.
    # However, due to the way kube_object classes are constructed (e.g., see
    # api_to_agent_daemonset) this is currently not possible. If we improve
    # this function to use a PodOwner method instead, we can side-step these
    # issues.
    return list(map(pod_lookup_from_api_pod, kube_object.pods(phase=api.Phase.RUNNING)))


def determine_pods_to_host(
    monitored_objects: Sequence[MonitoredObject],
    monitored_pods: Set[PodLookupName],
    cluster: Cluster,
    monitored_namespaces: Set[api.NamespaceName],
    api_pods: Sequence[api.Pod],
    resource_quotas: Sequence[api.ResourceQuota],
    monitored_api_namespaces: Sequence[api.Namespace],
    api_cron_jobs: Sequence[api.CronJob],
    piggyback_formatter: PBFormatter,
    piggyback_formatter_node: ObjectSpecificPBFormatter,
) -> PodsToHost:
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

            namespace_piggies.append(
                NamespacePiggy(
                    piggyback=piggyback_formatter(
                        object_type="namespace",
                        namespaced_name=namespace_name(api_namespace),
                    ),
                    pod_names=[pod_lookup_from_api_pod(pod) for pod in namespace_api_pods],
                    resource_quota_pod_names=resource_quota_pod_names,
                )
            )
    # TODO: write_object_sections_based_on_performance_pods is the equivalent
    # function based solely on api.Pod rather than class Pod. All objects relying
    # on write_sections_based_on_performance_pods should be refactored to use the
    # other function similar to namespaces
    piggybacks: list[Piggyback] = []
    if MonitoredObject.pods in monitored_objects:
        running_pods = pods_from_namespaces(
            filter_pods_by_phase(api_pods, api.Phase.RUNNING), monitored_namespaces
        )
        lookup_name_piggyback_mappings = {
            pod_lookup_from_api_pod(pod): pod_name(pod, prepend_namespace=True) for pod in api_pods
        }

        monitored_running_pods = monitored_pods.intersection(
            {pod_lookup_from_api_pod(pod) for pod in running_pods}
        )

        piggybacks.extend(
            Piggyback(
                piggyback=piggyback_formatter(
                    object_type="pod",
                    namespaced_name=lookup_name_piggyback_mappings[pod_name],
                ),
                pod_names=[pod_name],
            )
            for pod_name in monitored_running_pods
        )
    if MonitoredObject.nodes in monitored_objects:
        piggybacks.extend(
            Piggyback(
                piggyback=piggyback_formatter_node(node.name),
                pod_names=names,
            )
            for node in cluster.nodes
            if (names := _names_of_running_pods(node))
        )
    name_type_objects: Sequence[
        tuple[str, MonitoredObject, Sequence[Deployment | DaemonSet | StatefulSet]]
    ] = [
        ("deployment", MonitoredObject.deployments, cluster.deployments),
        ("statefulset", MonitoredObject.statefulsets, cluster.statefulsets),
        ("daemonset", MonitoredObject.daemonsets, cluster.daemonsets),
    ]
    for object_type_name, object_type, objects in name_type_objects:
        if object_type in monitored_objects:
            piggybacks.extend(
                Piggyback(
                    piggyback=piggyback_formatter(
                        object_type=object_type_name,
                        namespaced_name=k.name(prepend_namespace=True),
                    ),
                    pod_names=names,
                )
                for k in kube_objects_from_namespaces(objects, monitored_namespaces)
                if (names := _names_of_running_pods(k))
            )
    cluster_pods = list(
        map(
            pod_lookup_from_api_pod,
            filter_pods_by_phase(cluster.cluster_aggregation_pods, api.Phase.RUNNING),
        )
    )
    if MonitoredObject.cronjobs_pods in monitored_objects:
        piggybacks.extend(
            Piggyback(
                piggyback=piggyback_formatter(
                    object_type="cronjob",
                    namespaced_name=f"{k.metadata.namespace}_{k.metadata.name}",
                ),
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
        cluster_pods=cluster_pods,
        namespace_piggies=namespace_piggies,
    )


def write_sections_based_on_performance_pods(
    performance_pods: Mapping[PodLookupName, PerformancePod],
    pods_to_host: PodsToHost,
) -> None:
    # TODO: The usage of filter_outdated_and_non_monitored_pods here is really
    # inefficient. We can improve this, if we match the performance_pods to
    # sets of pod_names in a single go.
    LOGGER.info("Write piggyback sections based on performance data")
    for piggy in pods_to_host.piggybacks:
        pods = filter_outdated_and_non_monitored_pods(performance_pods.values(), piggy.pod_names)
        with ConditionalPiggybackSection(piggy.piggyback):
            for section_name, section_json in kube_object_performance_sections(pods):
                with SectionWriter(section_name) as writer:
                    writer.append(section_json)

    LOGGER.info("Write Namespace piggyback sections based on performance data")
    for piggy in pods_to_host.namespace_piggies:
        pods = filter_outdated_and_non_monitored_pods(performance_pods.values(), piggy.pod_names)
        resource_quota_pods = filter_outdated_and_non_monitored_pods(
            performance_pods.values(), piggy.pod_names
        )
        sections = kube_object_performance_sections(pods) + resource_quota_performance_sections(
            resource_quota_pods
        )
        with ConditionalPiggybackSection(piggy.piggyback):
            for section_name, section_json in sections:
                with SectionWriter(section_name) as writer:
                    writer.append(section_json)

    if cluster_performance_pods := filter_outdated_and_non_monitored_pods(
        performance_pods.values(), pods_to_host.cluster_pods
    ):
        LOGGER.info("Write cluster sections based on performance data")
        for section_name, section_json in kube_object_performance_sections(
            cluster_performance_pods
        ):
            with SectionWriter(section_name) as writer:
                writer.append(section_json)


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
    nodes_components: Dict[section.NodeName, Dict[str, section.NodeComponent]] = {}
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
    cluster_collector: Optional[section.ClusterCollectorMetadata] = None,
    node_collectors_metadata: Optional[Sequence[section.NodeMetadata]] = None,
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
    logs: List[section.CollectorHandlerLog], debug: bool = False
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


class CustomKubernetesApiException(Exception):
    def __init__(self, api_exception: client.ApiException) -> None:
        self.e = api_exception
        super().__init__()

    def __str__(self) -> str:
        """

        This is a modified version of __str__ method of client.kubernetes.ApiException.
        It strips the first \n in order make the output of plugin check-mk more verbose.
        """

        error_message_visible_in_check_mk_service_summary = (
            f"{self.e.status}, Reason: {self.e.reason}"
        )

        if self.e.body:
            error_message_visible_in_check_mk_service_summary += (
                f", Message: {json.loads(self.e.body).get('message')}"
            )

        return error_message_visible_in_check_mk_service_summary


def pod_conditions(pod_status: api.PodStatus) -> Optional[section.PodConditions]:
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
    return section.ContainerSpecs(
        containers={
            container_spec.name: section.ContainerSpec(
                image_pull_policy=container_spec.image_pull_policy,
            )
            for container_spec in pod_spec.containers
        }
    )


def pod_init_container_specs(pod_spec: api.PodSpec) -> section.ContainerSpecs:
    return section.ContainerSpecs(
        containers={
            container_spec.name: section.ContainerSpec(
                image_pull_policy=container_spec.image_pull_policy,
            )
            for container_spec in pod_spec.init_containers
        }
    )


def pod_start_time(pod_status: api.PodStatus) -> Optional[section.StartTime]:
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
                name=controller_namespaced_name(c),
            )
            for c in pod.controllers
        ],
        cluster=cluster_name,
        kubernetes_cluster_hostname=kubernetes_cluster_hostname,
    )


def write_api_pods_sections(
    cluster_name: str,
    annotation_key_pattern: AnnotationOption,
    pods: Sequence[api.Pod],
    kubernetes_cluster_hostname: str,
    piggyback_formatter: ObjectSpecificPBFormatter,
) -> None:
    def output_pod_sections(
        pod: api.Pod,
        cluster_name: str,
        annotation_key_pattern: AnnotationOption,
    ) -> None:
        sections = {
            "kube_pod_conditions_v1": lambda: pod_conditions(pod.status),
            "kube_pod_containers_v1": lambda: section.PodContainers(containers=pod.containers)
            if pod.containers
            else None,
            "kube_pod_container_specs_v1": lambda: pod_container_specs(pod.spec),
            "kube_pod_init_containers_v1": lambda: section.PodContainers(
                containers=pod.init_containers
            )
            if pod.init_containers
            else None,
            "kube_pod_init_container_specs_v1": lambda: pod_init_container_specs(pod.spec),
            "kube_start_time_v1": lambda: pod_start_time(pod.status),
            "kube_pod_lifecycle_v1": lambda: pod_lifecycle_phase(pod.status),
            "kube_pod_info_v1": lambda: pod_info(
                pod, cluster_name, kubernetes_cluster_hostname, annotation_key_pattern
            ),
            "kube_cpu_resources_v1": lambda: _collect_cpu_resources_from_api_pods([pod]),
            "kube_memory_resources_v1": lambda: _collect_memory_resources_from_api_pods([pod]),
        }
        _write_sections(sections)

    for pod in pods:
        with ConditionalPiggybackSection(
            piggyback_formatter(f"{pod_name(pod, prepend_namespace=True)}")
        ):
            output_pod_sections(pod, cluster_name, annotation_key_pattern)


def main(args: Optional[List[str]] = None) -> int:  # pylint: disable=too-many-branches
    if args is None:
        cmk.utils.password_store.replace_passwords()
        args = sys.argv[1:]
    arguments = parse_arguments(args)

    try:
        setup_logging(arguments.verbose)
        LOGGER.debug("parsed arguments: %s\n", arguments)

        with cmk.utils.profile.Profile(
            enabled=bool(arguments.profile), profile_file=arguments.profile
        ):
            api_client = make_api_client(arguments)
            LOGGER.info("Collecting API data")

            try:
                api_data = from_kubernetes(
                    api_client,
                    timeout=(arguments.k8s_api_connect_timeout, arguments.k8s_api_read_timeout),
                )
            except urllib3.exceptions.MaxRetryError as e:
                raise ClusterConnectionError(
                    f"Failed to establish a connection to {e.pool.host}:{e.pool.port} "
                    f"at URL {e.url}"
                ) from e
            except client.ApiException as e:
                raise CustomKubernetesApiException(e) from e

            # Namespaces are handled independently from the cluster object in order to improve
            # testability. The long term goal is to remove all objects from the cluster object
            cluster = Cluster.from_api_resources(
                excluded_node_roles=arguments.roles or [],
                pods=api_data.pods,
                nodes=api_data.nodes,
                deployments=api_data.deployments,
                daemon_sets=api_data.daemonsets,
                statefulsets=api_data.statefulsets,
                cluster_details=api_data.cluster_details,
            )

            # Sections based on API server data
            LOGGER.info("Write cluster sections based on API data")
            write_cluster_api_sections(arguments.cluster, cluster)

            monitored_namespace_names = filter_monitored_namespaces(
                {namespace_name(namespace) for namespace in api_data.namespaces},
                arguments.namespace_include_patterns,
                arguments.namespace_exclude_patterns,
            )
            piggyback_formatter = functools.partial(cluster_piggyback_formatter, arguments.cluster)
            piggyback_formatter_node: ObjectSpecificPBFormatter = functools.partial(
                piggyback_formatter, "node"
            )

            if MonitoredObject.nodes in arguments.monitored_objects:
                LOGGER.info("Write nodes sections based on API data")
                write_nodes_api_sections(
                    arguments.cluster,
                    arguments.annotation_key_pattern,
                    cluster.nodes,
                    kubernetes_cluster_hostname=arguments.kubernetes_cluster_hostname,
                    piggyback_formatter=piggyback_formatter_node,
                )

            if MonitoredObject.deployments in arguments.monitored_objects:
                LOGGER.info("Write deployments sections based on API data")
                write_deployments_api_sections(
                    arguments.cluster,
                    arguments.annotation_key_pattern,
                    kube_objects_from_namespaces(cluster.deployments, monitored_namespace_names),
                    kubernetes_cluster_hostname=arguments.kubernetes_cluster_hostname,
                    piggyback_formatter=functools.partial(piggyback_formatter, "deployment"),
                )

            resource_quotas = api_data.resource_quotas
            if MonitoredObject.namespaces in arguments.monitored_objects:
                LOGGER.info("Write namespaces sections based on API data")

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
                write_namespaces_api_sections(
                    arguments.cluster,
                    arguments.annotation_key_pattern,
                    monitored_api_namespaces,
                    resource_quotas,
                    api_data.pods,
                    kubernetes_cluster_hostname=arguments.kubernetes_cluster_hostname,
                    piggyback_formatter=functools.partial(piggyback_formatter, "namespace"),
                )

            if MonitoredObject.daemonsets in arguments.monitored_objects:
                LOGGER.info("Write daemon sets sections based on API data")
                write_daemon_sets_api_sections(
                    arguments.cluster,
                    arguments.annotation_key_pattern,
                    kube_objects_from_namespaces(cluster.daemonsets, monitored_namespace_names),
                    kubernetes_cluster_hostname=arguments.kubernetes_cluster_hostname,
                    piggyback_formatter=functools.partial(piggyback_formatter, "daemonset"),
                )

            if MonitoredObject.statefulsets in arguments.monitored_objects:
                LOGGER.info("Write StatefulSets sections based on API data")
                write_statefulsets_api_sections(
                    arguments.cluster,
                    arguments.annotation_key_pattern,
                    kube_objects_from_namespaces(cluster.statefulsets, monitored_namespace_names),
                    kubernetes_cluster_hostname=arguments.kubernetes_cluster_hostname,
                    piggyback_formatter=functools.partial(piggyback_formatter, "statefulset"),
                )

            monitored_pods: Set[PodLookupName] = {
                pod_lookup_from_api_pod(pod)
                for pod in pods_from_namespaces(api_data.pods, monitored_namespace_names)
            }

            # TODO: Currently there is no possibility for the user to specify whether to monitor CronJobs or not
            # The piggyback hosts will always be created, if there are any CronJobs in the cluster
            # Namespace filtering also needs to be added to the CronJobs
            monitored_api_cron_job_pods = [
                api_pod
                for cron_job in api_data.cron_jobs
                for api_pod in api_data.pods
                if api_pod.uid in cron_job.pod_uids
            ]
            write_cronjobs_api_sections(
                arguments.cluster,
                arguments.annotation_key_pattern,
                api_data.cron_jobs,
                monitored_api_cron_job_pods,
                {job.uid: job for job in api_data.jobs},
                kubernetes_cluster_hostname=arguments.kubernetes_cluster_hostname,
                piggyback_formatter=functools.partial(piggyback_formatter, "cronjob"),
            )

            if MonitoredObject.cronjobs_pods in arguments.monitored_objects:
                LOGGER.info("Write cronjob pods sections based on API data")
                write_api_pods_sections(
                    arguments.cluster,
                    arguments.annotation_key_pattern,
                    monitored_api_cron_job_pods,
                    kubernetes_cluster_hostname=arguments.kubernetes_cluster_hostname,
                    piggyback_formatter=functools.partial(piggyback_formatter, "pod"),
                )
            if MonitoredObject.pods in arguments.monitored_objects:
                LOGGER.info("Write pods sections based on API data")
                write_pods_api_sections(
                    arguments.cluster,
                    arguments.annotation_key_pattern,
                    [
                        pod
                        for pod in cluster.pods.values()
                        if pod_lookup_from_agent_pod(pod) in monitored_pods
                        and pod_lookup_from_agent_pod(pod)
                        not in [
                            f"{pod_name(pod, prepend_namespace=True)}"
                            for pod in monitored_api_cron_job_pods
                        ]
                    ],
                    kubernetes_cluster_hostname=arguments.kubernetes_cluster_hostname,
                    piggyback_formatter=functools.partial(piggyback_formatter, "pod"),
                )

            # Skip machine & container sections when cluster agent endpoint not configured
            if arguments.cluster_collector_endpoint is None:
                return 0

            # Sections based on cluster collector performance data
            cluster_collector_timeout = TCPTimeout(
                connect=arguments.cluster_collector_connect_timeout,
                read=arguments.cluster_collector_read_timeout,
            )

            # Handling of any of the cluster components should not crash the special agent as this
            # would discard all the API data. Special Agent failures of the Cluster Collector
            # components will not be highlighted in the usual Checkmk service but in a separate
            # service

            collector_metadata_logs: List[section.CollectorHandlerLog] = []
            with collector_exception_handler(logs=collector_metadata_logs, debug=arguments.debug):
                metadata_response = request_cluster_collector(
                    f"{arguments.cluster_collector_endpoint}/metadata",
                    arguments.token,
                    arguments.verify_cert_collector,
                    cluster_collector_timeout,
                    deserialize_http_proxy_config(arguments.cluster_collector_proxy),
                )

                metadata = section.Metadata(**metadata_response)
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

            collector_container_logs: List[section.CollectorHandlerLog] = []
            with collector_exception_handler(logs=collector_container_logs, debug=arguments.debug):
                LOGGER.info("Collecting container metrics from cluster collector")
                container_metrics: Sequence[RawMetrics] = request_cluster_collector(
                    f"{arguments.cluster_collector_endpoint}/container_metrics",
                    arguments.token,
                    arguments.verify_cert_collector,
                    cluster_collector_timeout,
                    deserialize_http_proxy_config(arguments.cluster_collector_proxy),
                )

                if not container_metrics:
                    raise CollectorHandlingException(
                        title="No data",
                        detail="No container metrics were collected from the cluster collector",
                    )

                try:
                    performance_pods = parse_and_group_containers_performance_metrics(
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
                    pods_to_host = determine_pods_to_host(
                        cluster=cluster,
                        monitored_pods=monitored_pods,
                        monitored_objects=arguments.monitored_objects,
                        monitored_namespaces=monitored_namespace_names,
                        api_pods=api_data.pods,
                        resource_quotas=resource_quotas,
                        api_cron_jobs=api_data.cron_jobs,
                        monitored_api_namespaces=monitored_api_namespaces,
                        piggyback_formatter=piggyback_formatter,
                        piggyback_formatter_node=piggyback_formatter_node,
                    )
                    write_sections_based_on_performance_pods(
                        performance_pods=performance_pods,
                        pods_to_host=pods_to_host,
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
            collector_machine_logs: List[section.CollectorHandlerLog] = []
            with collector_exception_handler(logs=collector_machine_logs, debug=arguments.debug):
                LOGGER.info("Collecting machine sections from cluster collector")
                machine_sections: List[Mapping[str, str]] = request_cluster_collector(
                    f"{arguments.cluster_collector_endpoint}/machine_sections",
                    arguments.token,
                    arguments.verify_cert_collector,
                    cluster_collector_timeout,
                    deserialize_http_proxy_config(arguments.cluster_collector_proxy),
                )

                if not machine_sections:
                    raise CollectorHandlingException(
                        title="No data",
                        detail="No machine sections were collected from the cluster collector",
                    )

                if MonitoredObject.nodes in arguments.monitored_objects:
                    try:
                        write_machine_sections(
                            cluster,
                            {s["node_name"]: s["sections"] for s in machine_sections},
                            piggyback_formatter_node,
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
