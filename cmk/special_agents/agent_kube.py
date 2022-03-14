#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Special agent for monitoring Kubernetes clusters. The fully supported API version of Kubernetes
depends on the corresponding python module. E.g. v11 of the python module will support mainly
Kubernetes API v1.15. Please take a look on the official website to see, if you API version
is supported: https://github.com/kubernetes-client/python
"""

from __future__ import annotations

import argparse
import contextlib
import functools
import json
import logging
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import (
    Any,
    Callable,
    Collection,
    DefaultDict,
    Dict,
    Iterator,
    List,
    Literal,
    Mapping,
    NamedTuple,
    NewType,
    Optional,
    Protocol,
    Sequence,
    Set,
    Union,
)
from urllib.parse import urlparse

import requests
import urllib3  # type: ignore[import]
from kubernetes import client  # type: ignore[import] # pylint: disable=import-error
from pydantic import BaseModel

import cmk.utils.password_store
import cmk.utils.paths
import cmk.utils.profile
from cmk.utils.http_proxy_config import deserialize_http_proxy_config, HTTPProxyConfig

from cmk.special_agents.utils import vcrtrace
from cmk.special_agents.utils.agent_common import ConditionalPiggybackSection, SectionWriter
from cmk.special_agents.utils_kubernetes.api_server import APIServer
from cmk.special_agents.utils_kubernetes.schemata import api, section

LOGGER = logging.getLogger()

AGENT_TMP_PATH = Path(cmk.utils.paths.tmp_dir, "agent_kube")

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
SectionName = NewType("SectionName", str)
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


class PerformancePod(NamedTuple):
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


class PathPrefixAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if not values:
            return ""
        path_prefix = "/" + values.strip("/")
        setattr(namespace, self.dest, path_prefix)


class TCPTimeout(BaseModel):
    connect: Optional[int]
    read: Optional[int]


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
    p.add_argument("--token", help="Token for that user")
    p.add_argument(
        "--monitored-objects",
        nargs="+",
        default=["deployments", "daemonsets", "statefulsets", "nodes", "pods"],
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


class PodOwner:
    def __init__(self):
        self._pods: List[Pod] = []

    def add_pod(self, pod: Pod) -> None:
        self._pods.append(pod)


class Pod:
    def __init__(
        self,
        uid: api.PodUID,
        metadata: api.PodMetaData,
        status: api.PodStatus,
        spec: api.PodSpec,
        containers: Mapping[str, api.ContainerStatus],
        init_containers: Mapping[str, api.ContainerStatus],
    ) -> None:
        self.uid = uid
        self.metadata = metadata
        self.spec = spec
        self.status = status
        self.containers = containers
        self.init_containers = init_containers
        self._controllers: List[Union[Deployment, DaemonSet, StatefulSet]] = []

    @property
    def phase(self):
        return self.status.phase

    @property
    def node(self) -> Optional[api.NodeName]:
        return self.spec.node

    def lifecycle_phase(self) -> section.PodLifeCycle:
        return section.PodLifeCycle(phase=self.phase)

    def name(self, prepend_namespace=False) -> str:
        if not prepend_namespace:
            return self.metadata.name

        return f"{self.metadata.namespace}_{self.metadata.name}"

    # TODO: Extract this method in order to remove the double linking to the controller
    def info(self, cluster_name: str) -> section.PodInfo:
        controllers = []
        for controller in self._controllers:
            controllers.append(
                section.Controller(
                    type_=section.ControllerType.from_str(controller.type_),
                    name=controller.name(),
                )
            )

        return section.PodInfo(
            namespace=self.metadata.namespace,
            name=self.metadata.name,
            creation_timestamp=self.metadata.creation_timestamp,
            labels=self.metadata.labels if self.metadata.labels else {},
            node=self.node,
            host_network=self.spec.host_network,
            dns_policy=self.spec.dns_policy,
            host_ip=self.status.host_ip,
            pod_ip=self.status.pod_ip,
            qos_class=self.status.qos_class,
            restart_policy=self.spec.restart_policy,
            uid=self.uid,
            controllers=controllers,
            cluster=cluster_name,
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

    def start_time(self) -> Optional[api.StartTime]:
        if self.status.start_time is None:
            return None
        return api.StartTime(start_time=self.status.start_time)

    def add_controller(self, controller: Union[Deployment, DaemonSet, StatefulSet]) -> None:
        """Add a handling controller of the pod

        Kubernetes control objects manage pods based on their labels. As the API does not
        provide any information regarding these control objects from the pod's perspective
        this double linking is done here
        """
        self._controllers.append(controller)


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


class CronJob(PodOwner):
    def __init__(self, metadata: api.MetaData, spec: api.CronJobSpec):
        super().__init__()
        self.metadata = metadata
        self.spec = spec

    def name(self, prepend_namespace: bool = True) -> str:
        if not prepend_namespace:
            return self.metadata.name
        return f"{self.metadata.namespace}_{self.metadata.name}"

    def pods(self) -> Sequence[Pod]:
        return self._pods


# TODO: addition of test framework for output sections
class Deployment(PodOwner):
    def __init__(
        self,
        metadata: api.MetaData,
        spec: api.DeploymentSpec,
        status: api.DeploymentStatus,
    ) -> None:
        super().__init__()
        self.metadata = metadata
        self.spec = spec
        self.status = status
        self.type_: str = "deployment"

    def add_pod(self, pod: Pod) -> None:
        super().add_pod(pod)
        pod.add_controller(self)

    def name(self, prepend_namespace: bool = False) -> str:
        if not prepend_namespace:
            return self.metadata.name

        return f"{self.metadata.namespace}_{self.metadata.name}"

    def pods(self, phase: Optional[api.Phase] = None) -> Sequence[Pod]:
        if phase is None:
            return self._pods
        return [pod for pod in self._pods if pod.phase == phase]

    def info(self, cluster_name: str) -> section.DeploymentInfo:
        container_images = set()
        container_names = []
        for pod in self._pods:
            if containers := pod.container_statuses():
                container_images.update(
                    {container.image for container in containers.containers.values()}
                )
                container_names.extend(
                    [container.name for container in containers.containers.values()]
                )

        return section.DeploymentInfo(
            name=self.name(),
            namespace=self.metadata.namespace,
            creation_timestamp=self.metadata.creation_timestamp,
            labels=self.metadata.labels if self.metadata.labels else {},
            selector=self.spec.selector,
            images=list(container_images),
            containers=container_names,
            cluster=cluster_name,
        )

    def pod_resources(self) -> section.PodResources:
        resources: DefaultDict[str, List[str]] = defaultdict(list)
        for pod in self._pods:
            resources[pod.phase].append(pod.name())
        return section.PodResources(**resources)

    def conditions(self) -> Optional[section.DeploymentConditions]:
        if not self.status.conditions:
            return None
        return section.DeploymentConditions(**self.status.conditions)

    def memory_resources(self) -> section.Resources:
        return _collect_memory_resources(self._pods)

    def cpu_resources(self) -> section.Resources:
        return _collect_cpu_resources(self._pods)

    def replicas(self) -> api.Replicas:
        return self.status.replicas

    def strategy(self) -> section.DeploymentStrategy:
        return section.DeploymentStrategy(strategy=self.spec.strategy)


class DaemonSet(PodOwner):
    def __init__(self, metadata: api.MetaData, spec: api.DaemonSetSpec) -> None:
        super().__init__()
        self.metadata = metadata
        self.spec = spec
        self.type_: str = "daemon_set"

    def name(self, prepend_namespace: bool = False) -> str:
        if not prepend_namespace:
            return self.metadata.name

        return f"{self.metadata.namespace}_{self.metadata.name}"

    def pods(self, phase: Optional[api.Phase] = None) -> Sequence[Pod]:
        if phase is None:
            return self._pods
        return [pod for pod in self._pods if pod.phase == phase]

    def add_pod(self, pod: Pod) -> None:
        super().add_pod(pod)
        pod.add_controller(self)

    def pod_resources(self) -> section.PodResources:
        resources: DefaultDict[str, List[str]] = defaultdict(list)
        for pod in self._pods:
            resources[pod.phase].append(pod.name())
        return section.PodResources(**resources)

    def memory_resources(self) -> section.Resources:
        return _collect_memory_resources(self._pods)

    def cpu_resources(self) -> section.Resources:
        return _collect_cpu_resources(self._pods)

    def strategy(self) -> section.DaemonSetStrategy:
        return section.DaemonSetStrategy(strategy=self.spec.strategy)


def daemonset_info(daemonset: DaemonSet, cluster_name: str) -> section.DaemonSetInfo:
    return section.DaemonSetInfo(
        name=daemonset.metadata.name,
        namespace=daemonset.metadata.namespace,
        creation_timestamp=daemonset.metadata.creation_timestamp,
        labels=daemonset.metadata.labels,
        selector=daemonset.spec.selector,
        cluster=cluster_name,
    )


class StatefulSet(PodOwner):
    def __init__(self, metadata: api.MetaData) -> None:
        super().__init__()
        self.metadata = metadata
        self.type_: str = "statefulset"

    def name(self, prepend_namespace: bool = False) -> str:
        if not prepend_namespace:
            return self.metadata.name
        return f"{self.metadata.namespace}_{self.metadata.name}"

    def pods(self, phase: Optional[api.Phase] = None) -> Sequence[Pod]:
        if phase is None:
            return self._pods
        return [pod for pod in self._pods if pod.phase == phase]

    def add_pod(self, pod: Pod) -> None:
        super().add_pod(pod)
        pod.add_controller(self)

    def memory_resources(self) -> section.Resources:
        return _collect_memory_resources(self._pods)

    def cpu_resources(self) -> section.Resources:
        return _collect_cpu_resources(self._pods)


class Node(PodOwner):
    def __init__(
        self,
        metadata: api.NodeMetaData,
        status: api.NodeStatus,
        resources: Dict[str, api.NodeResources],
        control_plane: bool,
        kubelet_info: api.KubeletInfo,
    ) -> None:
        super().__init__()
        self.metadata = metadata
        self.status = status
        self.resources = resources
        self.control_plane = control_plane
        self.kubelet_info = kubelet_info

    @property
    def name(self) -> api.NodeName:
        return api.NodeName(self.metadata.name)

    def pods(self, phase: Optional[api.Phase] = None) -> Sequence[Pod]:
        if phase is None:
            return self._pods
        return [pod for pod in self._pods if pod.phase == phase]

    def pod_resources(self) -> section.PodResources:
        resources: DefaultDict[str, List[str]] = defaultdict(list)
        for pod in self._pods:
            resources[pod.phase].append(pod.name())
        return section.PodResources(**resources)

    def allocatable_pods(self) -> section.AllocatablePods:
        return section.AllocatablePods(
            capacity=self.resources["capacity"].pods,
            allocatable=self.resources["allocatable"].pods,
        )

    def kubelet(self) -> api.KubeletInfo:
        return self.kubelet_info

    def info(self, cluster_name: str) -> section.NodeInfo:
        return section.NodeInfo(
            labels=self.metadata.labels,
            addresses=self.status.addresses,
            name=self.metadata.name,
            creation_timestamp=self.metadata.creation_timestamp,
            architecture=self.status.node_info.architecture,
            kernel_version=self.status.node_info.kernel_version,
            os_image=self.status.node_info.os_image,
            operating_system=self.status.node_info.operating_system,
            container_runtime_version=self.status.node_info.container_runtime_version,
            cluster=cluster_name,
        )

    def container_count(self) -> section.ContainerCount:
        result = section.ContainerCount()
        for pod in self._pods:
            for container in pod.containers.values():
                if container.state.type == "running":
                    result.running += 1
                elif container.state.type == "waiting":
                    result.waiting += 1
                else:
                    result.terminated += 1

        return result

    def memory_resources(self) -> section.Resources:
        return _collect_memory_resources(self._pods)

    def cpu_resources(self) -> section.Resources:
        return _collect_cpu_resources(self._pods)

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


class Cluster:
    @classmethod
    def from_api_resources(
        cls,
        pods: Sequence[api.Pod],
        nodes: Sequence[api.Node],
        statefulsets: Sequence[api.StatefulSet],
        deployments: Optional[Sequence[api.Deployment]] = None,
        cron_jobs: Optional[Sequence[api.CronJob]] = None,
        daemon_sets: Optional[Sequence[api.DaemonSet]] = None,
        cluster_details: Optional[api.ClusterDetails] = None,
    ) -> Cluster:
        """Creating and filling the Cluster with the Kubernetes Objects"""

        LOGGER.debug("Constructing k8s objects based on collected API data")

        _pod_owners_mapping: Dict[str, List[PodOwner]] = {}
        _nodes: Dict[api.NodeName, Node] = {}

        def _register_owner_for_pods(pod_controller: PodOwner, pod_uids: Sequence[api.PodUID]):
            for pod_uid in pod_uids:
                _pod_owners_mapping.setdefault(pod_uid, []).append(pod_controller)

        cluster = cls(cluster_details=cluster_details)
        for node_api in nodes:
            node = Node(
                node_api.metadata,
                node_api.status,
                node_api.resources,
                node_api.control_plane,
                node_api.kubelet_info,
            )
            cluster.add_node(node)
            _nodes[node.name] = node

        if deployments:
            for api_deployment in deployments:
                deployment = Deployment(
                    api_deployment.metadata, api_deployment.spec, api_deployment.status
                )
                cluster.add_deployment(deployment)
                _register_owner_for_pods(deployment, api_deployment.pods)

        if cron_jobs:
            for api_cron_job in cron_jobs:
                cron_job = CronJob(api_cron_job.metadata, api_cron_job.spec)
                cluster.add_cron_job(cron_job)
                _register_owner_for_pods(cron_job, api_cron_job.pod_uids)

        if daemon_sets:
            for api_daemon_set in daemon_sets:
                daemon_set = DaemonSet(
                    metadata=api_daemon_set.metadata,
                    spec=api_daemon_set.spec,
                )
                cluster.add_daemon_set(daemon_set)
                _register_owner_for_pods(daemon_set, api_daemon_set.pods)

        for api_statefulset in statefulsets:
            statefulset = StatefulSet(api_statefulset.metadata)
            cluster.add_statefulset(statefulset)
            _register_owner_for_pods(statefulset, api_statefulset.pods)

        owned_pods = set(_pod_owners_mapping.keys())
        present_pods = set(pod.uid for pod in pods)
        if not owned_pods.issubset(present_pods):
            raise ValueError(
                "The following owned pods are missing from the "
                f"API data: {list(owned_pods.difference(present_pods))}"
            )

        for api_pod in pods:
            pod = Pod(
                api_pod.uid,
                api_pod.metadata,
                api_pod.status,
                api_pod.spec,
                api_pod.containers,
                api_pod.init_containers,
            )
            cluster.add_pod(pod)
            if pod.node is not None:
                if pod.node not in _nodes:
                    raise ValueError(
                        f"Pod's ({api_pod.uid} {_nodes} {pod.node}) node is not present in the cluster"
                    )
                _nodes[pod.node].add_pod(pod)
            for pod_owner in _pod_owners_mapping.get(pod.uid, []):
                pod_owner.add_pod(pod)

        LOGGER.debug(
            "Cluster composition: Nodes (%s), Deployments (%s), DaemonSets (%s), StatefulSets (%s), Pods (%s)",
            len(cluster.nodes()),
            len(cluster.deployments()),
            len(cluster.daemon_sets()),
            len(cluster.statefulsets()),
            len(cluster.pods()),
        )
        return cluster

    def __init__(self, *, cluster_details: Optional[api.ClusterDetails] = None) -> None:
        self._cluster_details: Optional[api.ClusterDetails] = cluster_details
        self._cron_jobs: List[CronJob] = []
        self._daemon_sets: List[DaemonSet] = []
        self._statefulsets: List[StatefulSet] = []
        self._deployments: List[Deployment] = []
        self._nodes: Dict[api.NodeName, Node] = {}
        self._pods: Dict[str, Pod] = {}

    def add_node(self, node: Node) -> None:
        self._nodes[node.name] = node

    def add_cron_job(self, cron_job: CronJob) -> None:
        self._cron_jobs.append(cron_job)

    def add_deployment(self, deployment: Deployment) -> None:
        self._deployments.append(deployment)

    def add_daemon_set(self, daemon_set: DaemonSet) -> None:
        self._daemon_sets.append(daemon_set)

    def add_statefulset(self, statefulset: StatefulSet) -> None:
        self._statefulsets.append(statefulset)

    def add_pod(self, pod: Pod) -> None:
        self._pods[pod.uid] = pod

    def pod_resources(self) -> section.PodResources:
        resources: DefaultDict[str, List[str]] = defaultdict(list)
        for pod in self._pods.values():
            resources[pod.phase].append(pod.name())
        return section.PodResources(**resources)

    def allocatable_pods(self) -> section.AllocatablePods:
        return section.AllocatablePods(
            capacity=sum(node.resources["capacity"].pods for node in self._nodes.values()),
            allocatable=sum(node.resources["allocatable"].pods for node in self._nodes.values()),
        )

    def namespaces(self) -> Set[api.Namespace]:
        namespaces: Set[api.Namespace] = set()
        namespaces.update(api.Namespace(pod.metadata.namespace) for pod in self._pods.values())
        return namespaces

    def pods(self, phase: Optional[api.Phase] = None) -> Sequence[Pod]:
        if phase is None:
            return list(self._pods.values())
        return [pod for pod in self._pods.values() if pod.phase == phase]

    def nodes(self) -> Sequence[Node]:
        return list(self._nodes.values())

    def cron_jobs(self) -> Sequence[CronJob]:
        return self._cron_jobs

    def daemon_sets(self) -> Sequence[DaemonSet]:
        return self._daemon_sets

    def statefulsets(self) -> Sequence[StatefulSet]:
        return self._statefulsets

    def deployments(self) -> Sequence[Deployment]:
        return self._deployments

    def node_count(self) -> section.NodeCount:
        node_count = section.NodeCount()
        for node in self._nodes.values():
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

    def cluster_details(self) -> api.ClusterDetails:
        if self._cluster_details is None:
            raise AttributeError("cluster_details was not provided")
        return self._cluster_details

    def memory_resources(self) -> section.Resources:
        return _collect_memory_resources(list(self._pods.values()))

    def cpu_resources(self) -> section.Resources:
        return _collect_cpu_resources(list(self._pods.values()))

    def allocatable_memory_resource(self) -> section.AllocatableResource:
        return section.AllocatableResource(
            context="cluster",
            value=sum(node.resources["allocatable"].memory for node in self._nodes.values()),
        )

    def allocatable_cpu_resource(self) -> section.AllocatableResource:
        return section.AllocatableResource(
            context="cluster",
            value=sum(node.resources["allocatable"].cpu for node in self._nodes.values()),
        )


def _collect_memory_resources(pods: Sequence[Pod]) -> section.Resources:
    return aggregate_resources("memory", [c for pod in pods for c in pod.spec.containers])


def _collect_cpu_resources(pods: Sequence[Pod]) -> section.Resources:
    return aggregate_resources("cpu", [c for pod in pods for c in pod.spec.containers])


class JsonProtocol(Protocol):
    def json(self) -> str:
        ...


def _write_sections(sections: Mapping[str, Callable[[], Optional[JsonProtocol]]]) -> None:
    for section_name, section_call in sections.items():
        with SectionWriter(section_name) as writer:
            section_output = section_call()
            if not section_output:
                continue
            writer.append(section_output.json())


def write_cluster_api_sections(cluster_name: str, cluster: Cluster) -> None:
    sections = {
        "kube_pod_resources_v1": cluster.pod_resources,
        "kube_allocatable_pods_v1": cluster.allocatable_pods,
        "kube_node_count_v1": cluster.node_count,
        "kube_cluster_details_v1": cluster.cluster_details,
        "kube_memory_resources_v1": cluster.memory_resources,
        "kube_cpu_resources_v1": cluster.cpu_resources,
        "kube_allocatable_memory_resource_v1": cluster.allocatable_memory_resource,
        "kube_allocatable_cpu_resource_v1": cluster.allocatable_cpu_resource,
        "kube_cluster_info_v1": lambda: section.ClusterInfo(name=cluster_name),
    }
    _write_sections(sections)


def write_nodes_api_sections(
    cluster_name: str, api_nodes: Sequence[Node], piggyback_formatter: Callable[[str], str]
) -> None:
    def output_sections(cluster_node: Node) -> None:
        sections = {
            "kube_node_container_count_v1": cluster_node.container_count,
            "kube_node_kubelet_v1": cluster_node.kubelet,
            "kube_pod_resources_v1": cluster_node.pod_resources,
            "kube_allocatable_pods_v1": cluster_node.allocatable_pods,
            "kube_node_info_v1": lambda: cluster_node.info(cluster_name),
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
    api_deployments: Sequence[Deployment],
    piggyback_formatter: Callable[[str], str],
) -> None:
    """Write the deployment relevant sections based on k8 API information"""

    def output_sections(cluster_deployment: Deployment) -> None:
        sections = {
            "kube_pod_resources_v1": cluster_deployment.pod_resources,
            "kube_memory_resources_v1": cluster_deployment.memory_resources,
            "kube_deployment_info_v1": lambda: cluster_deployment.info(cluster_name),
            "kube_deployment_conditions_v1": cluster_deployment.conditions,
            "kube_cpu_resources_v1": cluster_deployment.cpu_resources,
            "kube_replicas_v1": cluster_deployment.replicas,
            "kube_deployment_strategy_v1": cluster_deployment.strategy,
        }
        _write_sections(sections)

    for deployment in api_deployments:
        with ConditionalPiggybackSection(
            piggyback_formatter(deployment.name(prepend_namespace=True))
        ):
            output_sections(deployment)


def write_daemon_sets_api_sections(
    cluster_name: str,
    api_daemon_sets: Sequence[DaemonSet],
    piggyback_formatter: Callable[[str], str],
) -> None:
    """Write the daemon set relevant sections based on k8 API information"""

    def output_sections(cluster_daemon_set: DaemonSet) -> None:
        sections = {
            "kube_pod_resources_v1": cluster_daemon_set.pod_resources,
            "kube_memory_resources_v1": cluster_daemon_set.memory_resources,
            "kube_cpu_resources_v1": cluster_daemon_set.cpu_resources,
            "kube_daemonset_info_v1": lambda: daemonset_info(cluster_daemon_set, cluster_name),
            "kube_daemonset_strategy_v1": cluster_daemon_set.strategy,
        }
        _write_sections(sections)

    for daemon_set in api_daemon_sets:
        with ConditionalPiggybackSection(
            piggyback_formatter(daemon_set.name(prepend_namespace=True))
        ):
            output_sections(daemon_set)


def write_statefulsets_api_sections(
    api_statefulsets: Sequence[StatefulSet], piggyback_formatter: Callable[[str], str]
) -> None:
    """Write the StatefulSet relevant sections based on k8 API information"""

    def output_sections(cluster_statefulset: StatefulSet) -> None:
        sections = {
            "kube_memory_resources_v1": cluster_statefulset.memory_resources,
            "kube_cpu_resources_v1": cluster_statefulset.cpu_resources,
        }
        _write_sections(sections)

    for statefulset in api_statefulsets:
        with ConditionalPiggybackSection(
            piggyback_formatter(statefulset.name(prepend_namespace=True))
        ):
            output_sections(statefulset)


def write_pods_api_sections(
    cluster_name: str, api_pods: Sequence[Pod], piggyback_formatter: Callable[[str], str]
) -> None:
    for pod in api_pods:
        with ConditionalPiggybackSection(piggyback_formatter(pod.name(prepend_namespace=True))):
            for section_name, section_content in pod_api_based_checkmk_sections(cluster_name, pod):
                if section_content is None:
                    continue
                with SectionWriter(section_name) as writer:
                    writer.append(section_content.json())


def write_machine_sections(
    cluster: Cluster,
    machine_sections: Mapping[str, str],
    piggyback_formatter_node: Callable[[str], str],
) -> None:
    # make sure we only print sections for nodes currently visible via Kubernetes api:
    for node in cluster.nodes():
        if sections := machine_sections.get(str(node.name)):
            with ConditionalPiggybackSection(piggyback_formatter_node(node.name)):
                sys.stdout.write(sections)


def pod_api_based_checkmk_sections(cluster_name: str, pod: Pod):
    sections = (
        ("kube_pod_conditions_v1", pod.conditions),
        ("kube_pod_containers_v1", pod.container_statuses),
        ("kube_pod_container_specs_v1", pod.container_specs),
        ("kube_pod_init_containers_v1", pod.init_container_statuses),
        ("kube_pod_init_container_specs_v1", pod.init_container_specs),
        ("kube_start_time_v1", pod.start_time),
        ("kube_pod_lifecycle_v1", pod.lifecycle_phase),
        ("kube_pod_info_v1", lambda: pod.info(cluster_name)),
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
    live_pods: Sequence[PerformancePod],
    lookup_name_to_piggyback_mappings: Set[PodLookupName],
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
    for live_pod in live_pods:
        if live_pod.lookup_name in lookup_name_to_piggyback_mappings:
            current_pods.append(live_pod)
            continue
        outdated_and_non_monitored_pods.append(live_pod.lookup_name)

    LOGGER.debug(
        "Outdated or non-monitored live pods: %s", ", ".join(outdated_and_non_monitored_pods)
    )
    return current_pods


def write_kube_object_performance_section(
    kube_obj: Union[Cluster, Node, Deployment, DaemonSet, StatefulSet],
    performance_pods: Mapping[PodLookupName, PerformancePod],
    piggyback_name: Optional[str] = None,
):
    """Write cluster, node & deployment sections based on collected performance metrics"""

    def write_object_sections(containers):
        # Memory section
        _write_performance_section(
            section_name=SectionName("memory"),
            section_output=section.PerformanceUsage(
                resource=section.Memory(
                    usage=_aggregate_metric(containers, MetricName("memory_working_set_bytes"))
                ),
            ),
        )

        # CPU section
        _write_performance_section(
            section_name=SectionName("cpu"),
            section_output=section.PerformanceUsage(
                resource=section.Cpu(
                    usage=_aggregate_rate_metric(containers, MetricName("cpu_usage_seconds_total")),
                ),
            ),
        )

    if not (pods := kube_obj.pods(phase=api.Phase.RUNNING)):
        return

    selected_pods = []
    for pod in pods:
        # Some pods which are running according to the Kubernetes API might not yet be
        # included in the performance data due to various reasons (e.g. pod just started)
        if (pod_lookup := pod_lookup_from_api_pod(pod)) not in performance_pods:
            # TODO: include logging without adding false positives
            continue
        selected_pods.append(performance_pods[pod_lookup])

    if not selected_pods:
        return

    containers = [container for pod in selected_pods for container in pod.containers]

    if piggyback_name is not None:
        with ConditionalPiggybackSection(piggyback_name):
            write_object_sections(containers)
    else:
        write_object_sections(containers)


def pod_performance_sections(pod: PerformancePod) -> None:
    """Write pod sections based on collected performance metrics"""
    if not pod.containers:
        return

    # CPU section
    _write_performance_section(
        section_name=SectionName("cpu"),
        section_output=section.PerformanceUsage(
            resource=section.Cpu(
                usage=_aggregate_rate_metric(pod.containers, MetricName("cpu_usage_seconds_total")),
            ),
        ),
    )

    # Memory section
    # the containers with "POD" in their cAdvisor generated name represent the container's
    # respective parent cgroup. A multitude of memory calculation references omit these for
    # container level calculations. We keep them as we calculate values at least on the pod level.
    _write_performance_section(
        section_name=SectionName("memory"),
        section_output=section.PerformanceUsage(
            resource=section.Memory(
                usage=_aggregate_metric(
                    pod.containers,
                    MetricName("memory_working_set_bytes"),
                ),
            ),
        ),
    )


def _aggregate_metric(
    containers: Sequence[PerformanceContainer],
    metric: MetricName,
) -> float:
    """Aggregate a metric across all containers"""
    return 0.0 + sum(
        [container.metrics[metric].value for container in containers if metric in container.metrics]
    )


def _aggregate_rate_metric(
    containers: Sequence[PerformanceContainer], rate_metric: MetricName
) -> float:
    """Aggregate a rate metric across all containers"""
    return 0.0 + sum(
        [
            container.rate_metrics[rate_metric].rate
            for container in containers
            if container.rate_metrics is not None and rate_metric in container.rate_metrics
        ]
    )


def _write_performance_section(section_name: SectionName, section_output: BaseModel):
    # TODO: change live to performance (including checks)
    with SectionWriter(f"kube_performance_{section_name}_v1") as writer:
        writer.append(section_output.json())


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
            proxies=proxy.to_requests_proxies(),
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


def map_lookup_name_to_piggyback_host_name(
    api_pods: Sequence[Pod], pod_lookup: Callable[[Pod], PodLookupName]
) -> Mapping[PodLookupName, PodNamespacedName]:
    return {
        pod_lookup(pod): PodNamespacedName(pod.name(prepend_namespace=True)) for pod in api_pods
    }


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
        proxies = http_proxy_config.to_requests_proxies() or {}
        proxies = session.merge_environment_settings(
            prep.url, proxies, session.stream, session.verify, session.cert
        )["proxies"]

    config.proxy = proxies.get(urlparse(host).scheme)
    config.proxy_headers = requests.adapters.HTTPAdapter().proxy_headers(config.proxy)

    if arguments.verify_cert_api:
        config.ssl_ca_cert = os.environ.get("REQUESTS_CA_BUNDLE")
    else:
        logging.info("Disabling SSL certificate verification")
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
                container_name=section.ContainerName(metric["container_name"]),
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
    counter_metrics, old_counter_metrics
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
    omit_metrics: Optional[Sequence[MetricName]] = None,
) -> Mapping[ContainerName, Mapping[MetricName, PerformanceMetric]]:
    if omit_metrics is None:
        omit_metrics = []

    containers: DefaultDict[ContainerName, Dict[MetricName, PerformanceMetric]] = defaultdict(dict)
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
            name=container_name, pod_lookup_name=lookup_func(metric)
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


def lookup_name(namespace: str, pod_name: str) -> PodLookupName:
    """Parse the pod lookup name

    This function parses an identifier which is used to match the pod based on the
    performance data to the associating pod based on the Kubernetes API data

    The namespace & pod name combination is unique across the cluster and is used instead of the pod
    uid due to a cAdvisor bug. This bug causes it to return the container config hash value
    (kubernetes.io/config.hash) as the pod uid for system containers and consequently differs to the
    uid reported by the Kubernetes API.
    """
    return PodLookupName(f"{namespace}_{pod_name}")


def pod_lookup_from_api_pod(api_pod: Pod) -> PodLookupName:
    return lookup_name(api_pod.metadata.namespace, api_pod.metadata.name)


def pod_lookup_from_metric(metric: Mapping[str, str]) -> PodLookupName:
    return lookup_name(metric["namespace"], metric["pod_name"])


def pods_from_namespaces(pods: Sequence[Pod], namespaces: Set[api.Namespace]) -> Sequence[Pod]:
    return [pod for pod in pods if pod.metadata.namespace in namespaces]


def deployments_from_namespaces(
    deployments: Sequence[Deployment], namespaces: Set[api.Namespace]
) -> Sequence[Deployment]:
    return [deployment for deployment in deployments if deployment.metadata.namespace in namespaces]


def statefulsets_from_namespaces(
    statefulsets: Sequence[StatefulSet], namespaces: Set[api.Namespace]
) -> Sequence[StatefulSet]:
    return [
        statefulset for statefulset in statefulsets if statefulset.metadata.namespace in namespaces
    ]


def filter_monitored_namespaces(
    cluster_namespaces: Set[api.Namespace],
    namespace_include_patterns: Sequence[str],
    namespace_exclude_patterns: Sequence[str],
) -> Set[api.Namespace]:
    """Filter Kubernetes namespaces based on the provided patterns

    Examples:
        >>> filter_monitored_namespaces({api.Namespace("foo"), api.Namespace("bar")}, ["foo"], [])
        {'foo'}

        >>> filter_monitored_namespaces({api.Namespace("foo"), api.Namespace("bar")}, [], ["foo"])
        {'bar'}

        >>> sorted(filter_monitored_namespaces({api.Namespace("foo"), api.Namespace("bar"),
        ... api.Namespace("man")}, ["foo", "bar"], []))
        ['bar', 'foo']

    """
    if (
        namespace_include_patterns and namespace_exclude_patterns
    ):  # this should be handled by argparse
        raise ValueError("It is not possible to define patterns for both filter mechanisms")

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
    kubernetes_namespaces: Set[api.Namespace], re_patterns: Sequence[str]
) -> Set[api.Namespace]:
    """Filter namespaces based on the provided regular expression patterns

    Examples:
         >>> sorted(_filter_namespaces({api.Namespace("foo"), api.Namespace("bar"),
         ... api.Namespace("man")}, ["foo", "man"]))
         ['foo', 'man']
    """
    filtered_namespaces = set()
    compiled_re = re.compile(f"({'|'.join(re_patterns)})")
    for namespace in kubernetes_namespaces:
        if compiled_re.match(namespace):
            filtered_namespaces.add(namespace)
    return filtered_namespaces


def cluster_piggyback_formatter(cluster_name: str, object_type: str, namespace_name: str) -> str:
    return f"{object_type}_{cluster_name}_{namespace_name}"


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


def write_sections_based_on_performance_pods(
    performance_pods: Mapping[PodLookupName, PerformancePod],
    monitored_objects: Sequence[str],
    monitored_pods: Set[PodLookupName],
    cluster: Cluster,
    monitored_namespaces: Set[api.Namespace],
    piggyback_formatter,
    piggyback_formatter_node,
):

    # Write performance sections
    if "pods" in monitored_objects:
        LOGGER.info("Write pod sections based on performance data")

        running_pods = pods_from_namespaces(
            cluster.pods(phase=api.Phase.RUNNING), monitored_namespaces
        )
        lookup_name_piggyback_mappings = map_lookup_name_to_piggyback_host_name(
            running_pods, pod_lookup_from_api_pod
        )
        monitored_running_pods = monitored_pods.intersection(
            {pod_lookup_from_api_pod(pod) for pod in running_pods}
        )

        for pod in filter_outdated_and_non_monitored_pods(
            list(performance_pods.values()), monitored_running_pods
        ):
            with ConditionalPiggybackSection(
                piggyback_formatter(
                    object_type="pod",
                    namespace_name=lookup_name_piggyback_mappings[pod.lookup_name],
                )
            ):
                pod_performance_sections(pod)

    if "nodes" in monitored_objects:
        LOGGER.info("Write node sections based on performance data")
        for node in cluster.nodes():
            write_kube_object_performance_section(
                node,
                performance_pods,
                piggyback_name=piggyback_formatter_node(node.name),
            )
    if "deployments" in monitored_objects:
        LOGGER.info("Write deployment sections based on performance data")
        for deployment in deployments_from_namespaces(cluster.deployments(), monitored_namespaces):
            write_kube_object_performance_section(
                deployment,
                performance_pods,
                piggyback_name=piggyback_formatter(
                    object_type="deployment",
                    namespace_name=deployment.name(prepend_namespace=True),
                ),
            )
    if "daemonsets" in monitored_objects:
        LOGGER.info("Write DaemonSet sections based on performance data")
        for daemonset in cluster.daemon_sets():
            write_kube_object_performance_section(
                daemonset,
                performance_pods,
                piggyback_name=piggyback_formatter(
                    object_type="daemonset", namespace_name=daemonset.name(prepend_namespace=True)
                ),
            )
    if "statefulsets" in monitored_objects:
        LOGGER.info("Write StatefulSet sections based on performance data")
        for statefulset in cluster.statefulsets():
            write_kube_object_performance_section(
                statefulset,
                performance_pods,
                piggyback_name=piggyback_formatter(
                    object_type="statefulset",
                    namespace_name=statefulset.name(prepend_namespace=True),
                ),
            )
    LOGGER.info("Write cluster sections based on performance data")
    write_kube_object_performance_section(cluster, performance_pods)


def _identify_unsupported_node_collector_components(
    nodes: Sequence[section.NodeMetadata], supported_max_major_version: int
):
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
):
    with SectionWriter("kube_collectors_metadata_v1") as writer:
        writer.append(
            section.CollectorComponentsMetadata(
                processing_log=processing_log,
                cluster_collector=cluster_collector,
                nodes=node_collectors_metadata,
            ).json()
        )


class CollectorHandlingException(Exception):
    # This exception is used as report medium for the Cluster Collector service
    def __init__(self, title: str, detail: str):
        self.title = title
        self.detail = detail
        super().__init__()

    def __str__(self):
        return f"{self.title}: {self.detail}" if self.detail else self.title


@contextlib.contextmanager
def collector_exception_handler(logs: List[section.CollectorHandlerLog], debug: bool = False):
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


def main(args: Optional[List[str]] = None) -> int:
    if args is None:
        cmk.utils.password_store.replace_passwords()
        args = sys.argv[1:]
    arguments = parse_arguments(args)

    try:
        setup_logging(arguments.verbose)
        logging.debug("parsed arguments: %s\n", arguments)

        with cmk.utils.profile.Profile(
            enabled=bool(arguments.profile), profile_file=arguments.profile
        ):
            api_client = make_api_client(arguments)
            LOGGER.info("Collecting API data")

            try:
                api_server = APIServer.from_kubernetes(
                    api_client,
                    timeout=(arguments.k8s_api_connect_timeout, arguments.k8s_api_read_timeout),
                )
            except urllib3.exceptions.MaxRetryError as e:
                raise ClusterConnectionError(
                    f"Failed to establish a connection to {e.pool.host}:{e.pool.port} "
                    f"at URL {e.url}"
                )

            cluster = Cluster.from_api_resources(
                pods=api_server.pods(),
                nodes=api_server.nodes(),
                deployments=api_server.deployments(),
                cron_jobs=api_server.cron_jobs(),
                daemon_sets=api_server.daemon_sets(),
                statefulsets=api_server.statefulsets(),
                cluster_details=api_server.cluster_details(),
            )

            # Sections based on API server data
            LOGGER.info("Write cluster sections based on API data")
            write_cluster_api_sections(arguments.cluster, cluster)

            monitored_namespaces = filter_monitored_namespaces(
                cluster.namespaces(),
                arguments.namespace_include_patterns,
                arguments.namespace_exclude_patterns,
            )
            piggyback_formatter = functools.partial(cluster_piggyback_formatter, arguments.cluster)
            piggyback_formatter_node: Callable[[str], str] = functools.partial(
                piggyback_formatter, "node"
            )

            if "nodes" in arguments.monitored_objects:
                LOGGER.info("Write nodes sections based on API data")
                write_nodes_api_sections(
                    arguments.cluster,
                    cluster.nodes(),
                    piggyback_formatter=piggyback_formatter_node,
                )

            if "deployments" in arguments.monitored_objects:
                LOGGER.info("Write deployments sections based on API data")
                write_deployments_api_sections(
                    arguments.cluster,
                    deployments_from_namespaces(cluster.deployments(), monitored_namespaces),
                    piggyback_formatter=functools.partial(piggyback_formatter, "deployment"),
                )

            if "daemonsets" in arguments.monitored_objects:
                LOGGER.info("Write daemon sets sections based on API data")
                write_daemon_sets_api_sections(
                    arguments.cluster,
                    [
                        daemonset
                        for daemonset in cluster.daemon_sets()
                        if daemonset.metadata.namespace in monitored_namespaces
                    ],
                    piggyback_formatter=functools.partial(piggyback_formatter, "daemonset"),
                )

            if "statefulsets" in arguments.monitored_objects:
                LOGGER.info("Write StatefulSets sections based on API data")
                write_statefulsets_api_sections(
                    statefulsets_from_namespaces(cluster.statefulsets(), monitored_namespaces),
                    piggyback_formatter=functools.partial(piggyback_formatter, "statefulset"),
                )

            monitored_pods: Set[PodLookupName] = {
                pod_lookup_from_api_pod(pod)
                for pod in pods_from_namespaces(cluster.pods(), monitored_namespaces)
            }

            if "cronjobs_pods" not in arguments.monitored_objects:
                # Ignore pods controlled by CronJobs
                monitored_pods = monitored_pods.difference(
                    {
                        pod_lookup_from_api_pod(pod)
                        for cron_job in cluster.cron_jobs()
                        for pod in cron_job.pods()
                    }
                )

            if "pods" in arguments.monitored_objects:
                LOGGER.info("Write pods sections based on API data")
                write_pods_api_sections(
                    arguments.cluster,
                    [
                        pod
                        for pod in cluster.pods()
                        if pod_lookup_from_api_pod(pod) in monitored_pods
                    ],
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
                    write_sections_based_on_performance_pods(
                        performance_pods=performance_pods,
                        cluster=cluster,
                        monitored_pods=monitored_pods,
                        monitored_objects=arguments.monitored_objects,
                        monitored_namespaces=monitored_namespaces,
                        piggyback_formatter=piggyback_formatter,
                        piggyback_formatter_node=piggyback_formatter_node,
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

            with SectionWriter("kube_processing_logs_v1") as writer:
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
