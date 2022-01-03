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
import json
import logging
import os
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import (
    Callable,
    DefaultDict,
    Dict,
    Iterator,
    List,
    Mapping,
    NamedTuple,
    NewType,
    Optional,
    Protocol,
    Sequence,
    Union,
)

import requests
import urllib3  # type: ignore[import]
from kubernetes import client  # type: ignore[import] # pylint: disable=import-error
from pydantic import BaseModel

import cmk.utils.password_store
import cmk.utils.paths
import cmk.utils.profile

from cmk.special_agents.utils.agent_common import ConditionalPiggybackSection, SectionWriter
from cmk.special_agents.utils_kubernetes.api_server import APIServer
from cmk.special_agents.utils_kubernetes.schemata import api, section

AGENT_TMP_PATH = Path(cmk.utils.paths.tmp_dir, "agent_kube")

MetricName = NewType("MetricName", str)
ContainerName = NewType("ContainerName", str)
SectionName = NewType("SectionName", str)


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
    pod_uid: api.PodUID
    metrics: Mapping[MetricName, PerformanceMetric]
    rate_metrics: Optional[Mapping[MetricName, RateMetric]]


class PerformancePod(NamedTuple):
    uid: api.PodUID
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
    pod_uid: api.PodUID


class PathPrefixAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if not values:
            return ""
        path_prefix = "/" + values.strip("/")
        setattr(namespace, self.dest, path_prefix)


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
    p.add_argument("--token", help="Token for that user")
    p.add_argument(
        "--api-server-endpoint", required=True, help="API server endpoint for Kubernetes API calls"
    )
    p.add_argument(
        "--cluster-agent-endpoint",
        required=True,
        help="Endpoint to query metrics from Kubernetes cluster agent",
    )

    p.add_argument("--verify-cert", action="store_true", help="Verify certificate")
    p.add_argument(
        "--profile",
        metavar="FILE",
        help="Profile the performance of the agent and write the output to a file",
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


class Pod:
    def __init__(
        self,
        uid: api.PodUID,
        metadata: api.MetaData,
        status: api.PodStatus,
        spec: api.PodSpec,
        containers: Mapping[str, api.ContainerInfo],
    ) -> None:
        self.uid = uid
        self.metadata = metadata
        self.spec = spec
        self.status = status
        self.containers = containers

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

    def info(self) -> section.PodInfo:
        return section.PodInfo(
            namespace=self.metadata.namespace,
            creation_timestamp=self.metadata.creation_timestamp,
            labels=self.metadata.labels if self.metadata.labels else {},
            node=self.node,
            restart_policy=self.spec.restart_policy,
            qos_class=self.status.qos_class,
            uid=self.uid,
        )

    def cpu_limit(self) -> section.AggregatedLimit:
        return aggregate_limit_values(
            [container.resources.limits.cpu for container in self.spec.containers]
        )

    def cpu_request(self) -> section.AggregatedRequest:
        return aggregate_request_values(
            [container.resources.requests.cpu for container in self.spec.containers]
        )

    def memory_limit(self) -> section.AggregatedLimit:
        return aggregate_limit_values(
            [container.resources.limits.memory for container in self.spec.containers]
        )

    def memory_request(self) -> section.AggregatedRequest:
        return aggregate_request_values(
            [container.resources.requests.memory for container in self.spec.containers]
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

    def containers_infos(self) -> Optional[section.PodContainers]:
        if not self.containers:
            return None
        return section.PodContainers(containers=self.containers)

    def start_time(self) -> Optional[api.StartTime]:
        if self.status.start_time is None:
            return None
        return api.StartTime(start_time=self.status.start_time)


def aggregate_request_values(
    request_values: Sequence[Optional[float]],
) -> section.AggregatedRequest:
    if None in request_values:
        return section.ExceptionalResource.unspecified
    return sum(request_values)  # type: ignore


def aggregate_limit_values(limit_values: Sequence[Optional[float]]) -> section.AggregatedLimit:
    contains_unspecified = None in limit_values
    contains_zero = 0 in limit_values
    if contains_unspecified and contains_zero:
        return section.ExceptionalResource.zero_unspecified
    if contains_zero:
        return section.ExceptionalResource.zero
    if contains_unspecified:
        return section.ExceptionalResource.unspecified
    return sum(limit_values)  # type: ignore


class Deployment:
    def __init__(self, metadata: api.MetaData, status: api.DeploymentStatus) -> None:
        self.metadata = metadata
        self.status = status
        self._pods: List[Pod] = []

    def name(self, prepend_namespace: bool = False) -> str:
        if not prepend_namespace:
            return self.metadata.name

        return f"{self.metadata.namespace}_{self.metadata.name}"

    def pods(self, phase: Optional[api.Phase] = None) -> Sequence[Pod]:
        if phase is None:
            return self._pods
        return [pod for pod in self._pods if pod.phase == phase]

    def info(self) -> section.DeploymentInfo:
        container_images = set()
        container_names = []
        for pod in self._pods:
            if containers := pod.containers_infos():
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
            images=list(container_images),
            containers=container_names,
        )

    def add_pod(self, pod: Pod) -> None:
        self._pods.append(pod)

    def pod_resources(self) -> section.PodResources:
        resources: DefaultDict[str, List[str]] = defaultdict(list)
        for pod in self._pods:
            resources[pod.phase].append(pod.name())
        return section.PodResources(**resources)

    def conditions(self) -> section.DeploymentConditions:
        return section.DeploymentConditions(conditions=self.status.conditions)

    def memory_resources(self) -> section.Resources:
        return _collect_memory_resources(self._pods)

    def cpu_resources(self) -> section.Resources:
        return _collect_cpu_resources(self._pods)


class Node:
    def __init__(
        self,
        metadata: api.MetaData,
        status: api.NodeStatus,
        resources: Dict[str, api.NodeResources],
        control_plane: bool,
        kubelet_info: api.KubeletInfo,
    ) -> None:
        self.metadata = metadata
        self.status = status
        self.resources = resources
        self.control_plane = control_plane
        self.kubelet_info = kubelet_info
        self._pods: List[Pod] = []

    @property
    def name(self) -> api.NodeName:
        return api.NodeName(self.metadata.name)

    def append(self, pod: Pod) -> None:
        self._pods.append(pod)

    def pods(self, phase: Optional[api.Phase] = None) -> Sequence[Pod]:
        if phase is None:
            return self._pods
        return [pod for pod in self._pods if pod.phase == phase]

    def pod_resources(self) -> section.PodResourcesWithCapacity:
        resources = {
            "capacity": self.resources["capacity"].pods,
            "allocatable": self.resources["allocatable"].pods,
        }
        phases_pods = defaultdict(list)
        for pod in self._pods:
            phases_pods[pod.phase].append(pod.name())
        resources.update(phases_pods)
        return section.PodResourcesWithCapacity(**resources)

    def kubelet(self) -> api.KubeletInfo:
        return self.kubelet_info

    def info(self) -> section.NodeInfo:
        return section.NodeInfo(labels=self.metadata.labels, **dict(self.status.node_info))

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


class Cluster:
    @classmethod
    def from_api_server(cls, api_server: api.API) -> Cluster:
        cluster_details = api_server.cluster_details()

        cluster = cls(cluster_details=cluster_details)
        for node_api in api_server.nodes():
            node = Node(
                node_api.metadata,
                node_api.status,
                node_api.resources,
                node_api.control_plane,
                node_api.kubelet_info,
            )
            cluster.add_node(node)

        for pod in api_server.pods():
            cluster.add_pod(
                Pod(
                    pod.uid,
                    pod.metadata,
                    pod.status,
                    pod.spec,
                    pod.containers,
                )
            )

        for deployment in api_server.deployments():
            cluster.add_deployment(
                Deployment(deployment.metadata, deployment.status), deployment.pods
            )

        return cluster

    def __init__(self, *, cluster_details: Optional[api.ClusterInfo] = None) -> None:
        self._nodes: Dict[api.NodeName, Node] = {}
        self._deployments: List[Deployment] = []
        self._pods: Dict[str, Pod] = {}
        self._cluster_details: Optional[api.ClusterInfo] = cluster_details

    def add_node(self, node: Node) -> None:
        self._nodes[node.name] = node

    def add_deployment(self, deployment: Deployment, pod_uids: Sequence[api.PodUID]) -> None:
        for pod_uid in pod_uids:
            try:
                deployment.add_pod(self._pods[pod_uid])
            except KeyError:
                raise KeyError(f"Pod {pod_uid} for deployment {deployment.name()} does not exist")
        self._deployments.append(deployment)

    def add_pod(self, pod: Pod) -> None:
        if pod.node is not None:
            if pod.node not in self._nodes:
                raise KeyError(f"Node {pod.node} of {pod.name} was not listed in the API")
            self._nodes[pod.node].append(pod)
        self._pods[pod.uid] = pod

    def pod_resources(self) -> section.PodResourcesWithCapacity:
        resources = {
            "capacity": sum(node.resources["capacity"].pods for node in self._nodes.values()),
            "allocatable": sum(node.resources["allocatable"].pods for node in self._nodes.values()),
        }
        phases_pods = defaultdict(list)
        for pod in self._pods.values():
            phases_pods[pod.phase].append(pod.name())
        resources.update(phases_pods)
        return section.PodResourcesWithCapacity(**resources)

    def pods(self, phase: Optional[api.Phase] = None) -> Sequence[Pod]:
        if phase is None:
            return list(self._pods.values())
        return [pod for pod in self._pods.values() if pod.phase == phase]

    def nodes(self) -> Sequence[Node]:
        return list(self._nodes.values())

    def deployments(self) -> Sequence[Deployment]:
        return self._deployments

    def node_count(self) -> section.NodeCount:
        worker = 0
        control_plane = 0
        for node in self._nodes.values():
            if node.control_plane:
                control_plane += 1
            else:
                worker += 1
        return section.NodeCount(worker=worker, control_plane=control_plane)

    def cluster_details(self) -> api.ClusterInfo:
        if self._cluster_details is None:
            raise AttributeError("cluster_details was not provided")
        return self._cluster_details

    def memory_resources(self) -> section.Resources:
        return _collect_memory_resources(list(self._pods.values()))

    def cpu_resources(self) -> section.Resources:
        return _collect_cpu_resources(list(self._pods.values()))


# TODO aggregating this by combining the values from pods duplicates some of logic (compare this
# function to aggregate_limit_values). In the future, Kubernetes objects such as cluster should
# use aggregate_limit_values.
def aggregate_limit_values_from_pods(
    limit_values: Sequence[section.AggregatedLimit],
) -> section.AggregatedLimit:
    if section.ExceptionalResource.zero_unspecified in limit_values:
        return section.ExceptionalResource.zero_unspecified
    contains_unspecified = section.ExceptionalResource.unspecified in limit_values
    contains_zero = section.ExceptionalResource.zero in limit_values
    if contains_zero and contains_unspecified:
        return section.ExceptionalResource.zero_unspecified
    if contains_unspecified:
        return section.ExceptionalResource.unspecified
    if contains_zero:
        return section.ExceptionalResource.zero
    return sum(limit_values)


def aggregate_request_values_from_pods(
    request_values: Sequence[section.AggregatedRequest],
) -> section.AggregatedRequest:
    if section.ExceptionalResource.unspecified in request_values:
        return section.ExceptionalResource.unspecified
    return sum(request_values)


def _collect_memory_resources(pods: Sequence[Pod]) -> section.Resources:
    return section.Resources(
        limit=aggregate_limit_values_from_pods([pod.memory_limit() for pod in pods]),
        request=aggregate_request_values_from_pods([pod.memory_request() for pod in pods]),
    )


def _collect_cpu_resources(pods: Sequence[Pod]) -> section.Resources:
    return section.Resources(
        limit=aggregate_limit_values_from_pods([pod.cpu_limit() for pod in pods]),
        request=aggregate_request_values_from_pods([pod.cpu_request() for pod in pods]),
    )


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


def write_cluster_api_sections(cluster: Cluster) -> None:
    sections = {
        "kube_pod_resources_with_capacity_v1": cluster.pod_resources,
        "kube_node_count_v1": cluster.node_count,
        "kube_cluster_details_v1": cluster.cluster_details,
        "kube_memory_resources_v1": cluster.memory_resources,
        "kube_cpu_resources_v1": cluster.cpu_resources,
    }
    _write_sections(sections)


def write_nodes_api_sections(api_nodes: Sequence[Node]) -> None:
    def output_sections(cluster_node: Node) -> None:
        sections = {
            "kube_node_container_count_v1": cluster_node.container_count,
            "kube_node_kubelet_v1": cluster_node.kubelet,
            "kube_pod_resources_with_capacity_v1": cluster_node.pod_resources,
            "kube_node_info_v1": cluster_node.info,
            "kube_cpu_resources_v1": cluster_node.cpu_resources,
            "kube_memory_resources_v1": cluster_node.memory_resources,
        }
        _write_sections(sections)

    for node in api_nodes:
        with ConditionalPiggybackSection(f"node_{node.name}"):
            output_sections(node)


def write_deployments_api_sections(api_deployments: Sequence[Deployment]) -> None:
    """Write the deployment relevant sections based on k8 API information"""

    def output_sections(cluster_deployment: Deployment) -> None:
        sections = {
            "kube_pod_resources_v1": cluster_deployment.pod_resources,
            "kube_memory_resources_v1": cluster_deployment.memory_resources,
            "kube_deployment_info_v1": cluster_deployment.info,
            "kube_deployment_conditions_v1": cluster_deployment.conditions,
            "kube_cpu_resources_v1": cluster_deployment.cpu_resources,
        }
        _write_sections(sections)

    for deployment in api_deployments:
        with ConditionalPiggybackSection(f"deployment_{deployment.name(prepend_namespace=True)}"):
            output_sections(deployment)


def write_pods_api_sections(api_pods: Sequence[Pod]) -> None:
    for pod in api_pods:
        with ConditionalPiggybackSection(f"pod_{pod.name(prepend_namespace=True)}"):
            for section_name, section_content in pod_api_based_checkmk_sections(pod):
                if section_content is None:
                    continue
                with SectionWriter(section_name) as writer:
                    writer.append(section_content.json())


def pod_api_based_checkmk_sections(pod: Pod):
    sections = (
        ("k8s_pod_conditions_v1", pod.conditions),
        ("kube_pod_containers_v1", pod.containers_infos),
        ("kube_start_time_v1", pod.start_time),
        ("kube_pod_lifecycle_v1", pod.lifecycle_phase),
        ("kube_pod_info_v1", pod.info),
        (
            "kube_cpu_resources_v1",
            lambda: section.Resources(limit=pod.cpu_limit(), request=pod.cpu_request()),
        ),
        (
            "kube_memory_resources_v1",
            lambda: section.Resources(limit=pod.memory_limit(), request=pod.memory_request()),
        ),
    )
    for section_name, section_call in sections:
        yield section_name, section_call()


def filter_outdated_pods(
    live_pods: Sequence[PerformancePod], uid_piggyback_mappings: Mapping[api.PodUID, str]
) -> Iterator[PerformancePod]:
    return (live_pod for live_pod in live_pods if live_pod.uid in uid_piggyback_mappings)


def write_kube_object_performance_section(
    kube_obj: Union[Cluster, Node, Deployment],
    performance_pods: Mapping[api.PodUID, PerformancePod],
    piggyback_name: Optional[str] = None,
):
    """Write cluster, node & deployment sections based on collected performance metrics"""

    def write_object_sections(containers):
        # Memory section
        _write_performance_section(
            section_name=SectionName("memory"),
            section_output=section.Memory(
                memory_usage_bytes=_aggregate_metric(containers, MetricName("memory_usage_bytes")),
            ),
        )
        # CPU section
        _write_performance_section(
            section_name=SectionName("cpu_usage"),
            section_output=section.CpuUsage(
                usage=_aggregate_rate_metric(containers, MetricName("cpu_usage_seconds_total")),
            ),
        )

    if not (pods := kube_obj.pods(phase=api.Phase.RUNNING)):
        return

    selected_pods = [performance_pods[pod.uid] for pod in pods if pod.uid in performance_pods]
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
        section_name=SectionName("cpu_usage"),
        section_output=section.CpuUsage(
            usage=_aggregate_rate_metric(pod.containers, MetricName("cpu_usage_seconds_total")),
        ),
    )

    # Memory section
    _write_performance_section(
        section_name=SectionName("memory"),
        section_output=section.Memory(
            memory_usage_bytes=_aggregate_metric(pod.containers, MetricName("memory_usage_bytes")),
        ),
    )


def _aggregate_metric(containers: Sequence[PerformanceContainer], metric: MetricName) -> float:
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
    with SectionWriter(f"k8s_live_{section_name}_v1") as writer:
        writer.append(section_output.json())


class DefinitionError(Exception):
    pass


class SetupError(Exception):
    pass


def request_metrics_from_cluster_collector(
    cluster_agent_url: str, verify: bool
) -> Sequence[Mapping[str, str]]:
    cluster_resp = requests.get(
        f"{cluster_agent_url}/container_metrics", verify=verify
    )  # TODO: certificate validation
    if cluster_resp.status_code != 200:
        raise SetupError("Checkmk cannot make a connection to the k8 cluster agent")

    if not cluster_resp.content:
        raise SetupError("Worker nodes")

    resp_content = cluster_resp.content.decode("utf-8").split("\n")
    return json.loads(resp_content[0])


def map_uid_to_piggyback_host_name(api_pods: Sequence[Pod]) -> Mapping[api.PodUID, str]:
    return {pod.uid: pod.name(prepend_namespace=True) for pod in api_pods}


def make_api_client(arguments: argparse.Namespace) -> client.ApiClient:
    config = client.Configuration()

    host = arguments.api_server_endpoint
    config.host = host
    if arguments.token:
        config.api_key_prefix["authorization"] = "Bearer"
        config.api_key["authorization"] = arguments.token

    if arguments.verify_cert:
        config.ssl_ca_cert = os.environ.get("REQUESTS_CA_BUNDLE")
    else:
        logging.info("Disabling SSL certificate verification")
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        config.verify_ssl = False

    return client.ApiClient(config)


def parse_performance_metrics(
    cluster_collector_metrics: Sequence[Mapping[str, str]]
) -> Sequence[PerformanceMetric]:
    metrics = []
    for metric in cluster_collector_metrics:
        if " " in (metric_value := metric["metric_value_string"]):
            metric_value, timestamp = metric_value.split(" ")
            metric_timestamp = float(timestamp) / 1000.0
        else:
            metric_timestamp = time.time()

        metric_name = metric["metric_name"].replace("container_", "", 1)
        metrics.append(
            PerformanceMetric(
                container_name=section.ContainerName(metric["container_name"]),
                name=MetricName(metric_name),
                value=metric_value,
                timestamp=metric_timestamp,
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

    containers = {}
    for container in containers_counters.values():
        if (old_container := containers_counters_old.get(container.name)) is None:
            continue

        container_rate_metrics = container_available_rate_metrics(
            container.metrics, old_container.metrics
        )
        containers[container.name] = container_rate_metrics
    return containers


def container_available_rate_metrics(
    counter_metrics, old_counter_metrics
) -> Mapping[MetricName, RateMetric]:
    rate_metrics = {}
    for counter_metric in counter_metrics.values():
        if counter_metric.name not in old_counter_metrics:
            continue

        rate_metrics[counter_metric.name] = RateMetric(
            name=counter_metric.name,
            rate=calculate_rate(counter_metric, old_counter_metrics[counter_metric.name]),
        )
    return rate_metrics


def calculate_rate(counter_metric: CounterMetric, old_counter_metric: CounterMetric) -> float:
    time_delta = counter_metric.timestamp - old_counter_metric.timestamp
    return (counter_metric.value - old_counter_metric.value) / time_delta


def load_containers_store(path: Path, file_name: str) -> ContainersStore:
    try:
        with open(f"{path}/{file_name}", "r") as f:
            return ContainersStore(**json.loads(f.read()))
    except FileNotFoundError:
        logging.debug("Could not find metrics file. This is expected if the first run.")
    except SyntaxError:
        logging.debug("Found metrics file, but could not parse it.")
    return ContainersStore(containers={})


def persist_containers_store(containers_store: ContainersStore, path: Path, file_name: str) -> None:
    path.mkdir(parents=True, exist_ok=True)
    with open(f"{path}/{file_name}", "w") as f:
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
) -> Mapping[api.PodUID, PerformancePod]:
    parsed_pods: Dict[api.PodUID, List[PerformanceContainer]] = {}
    for container in performance_containers:
        pod_containers = parsed_pods.setdefault(container.pod_uid, [])
        pod_containers.append(container)
    return {
        pod_uid: PerformancePod(uid=pod_uid, containers=containers)
        for pod_uid, containers in parsed_pods.items()
    }


def parse_containers_metadata(metrics) -> Mapping[ContainerName, ContainerMetadata]:
    containers = {}
    for metric in metrics:
        if (container_name := metric["container_name"]) in containers:
            continue
        containers[ContainerName(container_name)] = ContainerMetadata(
            name=container_name, pod_uid=api.PodUID(metric["pod_uid"])
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
            pod_uid=container.pod_uid,
            metrics=containers_metrics[container.name],
            rate_metrics=containers_rate_metrics.get(container.name),
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
            api_server = APIServer.from_kubernetes(api_client)

            cluster = Cluster.from_api_server(api_server)

            # Sections based on API server data
            write_cluster_api_sections(cluster)
            write_nodes_api_sections(cluster.nodes())
            write_deployments_api_sections(cluster.deployments())
            write_pods_api_sections(cluster.pods())  # TODO: make more explicit

            # Sections based on cluster collector performance data
            collected_metrics = request_metrics_from_cluster_collector(
                arguments.cluster_agent_endpoint, arguments.verify_cert
            )
            performance_metrics = parse_performance_metrics(collected_metrics)

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

            # TODO: file_name must be adjusted when adding multi-cluster/rule support later
            store_file_name = "containers_counters.json"
            previous_cycle_store = load_containers_store(
                path=AGENT_TMP_PATH, file_name=store_file_name
            )
            containers_rate_metrics = determine_rate_metrics(
                current_cycle_store.containers, previous_cycle_store.containers
            )
            persist_containers_store(
                current_cycle_store, path=AGENT_TMP_PATH, file_name=store_file_name
            )

            containers_metrics = group_metrics_by_container(
                performance_metrics, omit_metrics=relevant_counter_metrics
            )
            containers_metadata = parse_containers_metadata(collected_metrics)
            performance_containers = group_container_components(
                containers_metadata, containers_metrics, containers_rate_metrics
            )

            performance_pods = group_containers_by_pods(performance_containers)

            uid_piggyback_mappings = map_uid_to_piggyback_host_name(cluster.pods())

            # Write performance sections
            for pod in filter_outdated_pods(
                list(performance_pods.values()), uid_piggyback_mappings
            ):
                with ConditionalPiggybackSection(f"pod_{uid_piggyback_mappings[pod.uid]}"):
                    pod_performance_sections(pod)

            for node in cluster.nodes():
                write_kube_object_performance_section(
                    node,
                    performance_pods,
                    piggyback_name=f"node_{node.name}",
                )

            for deployment in cluster.deployments():
                write_kube_object_performance_section(
                    deployment,
                    performance_pods,
                    piggyback_name=f"deployment_{deployment.name(prepend_namespace=True)}",
                )

            # TODO: make name configurable when introducing multi-cluster support
            # remember that host with k8 rule must have at least one service
            write_kube_object_performance_section(cluster, performance_pods)

            # TODO: handle pods with no performance data (pod.uid not in performance pods)

    except urllib3.exceptions.MaxRetryError as e:
        if arguments.debug:
            raise
        if isinstance(e.reason, urllib3.exceptions.NewConnectionError):
            sys.stderr.write(
                "Failed to establish a connection to %s:%s at URL %s"
                % (e.pool.host, e.pool.port, e.url)
            )
        else:
            sys.stderr.write("%s" % e)
        return 1
    except Exception as e:
        if arguments.debug:
            raise
        sys.stderr.write("%s" % e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
