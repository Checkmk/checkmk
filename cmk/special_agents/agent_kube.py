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
from typing import (
    Callable,
    DefaultDict,
    Dict,
    Iterable,
    Iterator,
    List,
    Mapping,
    NamedTuple,
    NewType,
    Optional,
    Protocol,
    Sequence,
    Type,
)

import requests
import urllib3  # type: ignore[import]
from kubernetes import client  # type: ignore[import] # pylint: disable=import-error
from pydantic import BaseModel

import cmk.utils.password_store
import cmk.utils.profile

from cmk.special_agents.utils.agent_common import ConditionalPiggybackSection, SectionWriter
from cmk.special_agents.utils_kubernetes.api_server import APIServer
from cmk.special_agents.utils_kubernetes.schemata import api, section

MetricName = NewType("MetricName", str)
PodUID = NewType("PodUID", str)
SectionName = NewType("SectionName", str)


class PerformancePod(NamedTuple):
    uid: PodUID
    containers: List[PerformanceContainer]


class PerformanceContainer(NamedTuple):
    name: section.ContainerName
    metrics: Mapping[MetricName, section.PerformanceMetric]
    pod_uid: PodUID


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
        uid: str,
        metadata: api.MetaData,
        status: api.PodStatus,
        spec: api.PodSpec,
        resources: api.PodUsageResources,
        containers: Mapping[str, api.ContainerInfo],
    ) -> None:
        self.uid = PodUID(uid)
        self.metadata = metadata
        self.node = spec.node
        self.status = status
        self.resources = resources
        self.containers = containers

    @property
    def phase(self):
        return self.status.phase

    def lifecycle_phase(self) -> section.PodLifeCycle:
        return section.PodLifeCycle(phase=self.phase)

    def name(self, prepend_namespace=False) -> str:
        if not prepend_namespace:
            return self.metadata.name

        return f"{self.metadata.namespace}_{self.metadata.name}"

    def cpu_resources(self) -> api.Resources:
        return api.Resources(
            limit=self.resources.cpu.limit,
            requests=self.resources.cpu.requests,
        )

    def memory_resources(self) -> api.Resources:
        return api.Resources(
            limit=self.resources.memory.limit, requests=self.resources.memory.requests
        )

    def conditions(self) -> section.PodConditions:
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

    def memory_resources(self) -> api.Resources:
        return _collect_memory_resources(self._pods)


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

    def memory_resources(self) -> api.Resources:
        return _collect_memory_resources(self._pods)


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
                    pod.resources,
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

    def memory_resources(self) -> api.Resources:
        return _collect_memory_resources(list(self._pods.values()))


def _collect_memory_resources(pods: Sequence[Pod]) -> api.Resources:
    resources: DefaultDict[str, float] = defaultdict(float)
    for pod in pods:
        for k, v in dict(pod.memory_resources()).items():
            resources[k] += v
    return api.Resources(**resources)


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


def output_cluster_api_sections(cluster: Cluster) -> None:
    sections = {
        "kube_pod_resources_with_capacity_v1": cluster.pod_resources,
        "kube_node_count_v1": cluster.node_count,
        "kube_cluster_details_v1": cluster.cluster_details,
        "kube_memory_resources_v1": cluster.memory_resources,
    }
    _write_sections(sections)


def output_nodes_api_sections(api_nodes: Sequence[Node]) -> None:
    def output_sections(cluster_node: Node) -> None:
        sections = {
            "kube_node_container_count_v1": cluster_node.container_count,
            "kube_node_kubelet_v1": cluster_node.kubelet,
            "kube_pod_resources_with_capacity_v1": cluster_node.pod_resources,
            "kube_node_info_v1": cluster_node.info,
        }
        _write_sections(sections)

    for node in api_nodes:
        with ConditionalPiggybackSection(f"node_{node.name}"):
            output_sections(node)


def output_deployments_api_sections(api_deployments: Sequence[Deployment]) -> None:
    """Write the deployment relevant sections based on k8 API information"""

    def output_sections(cluster_deployment: Deployment) -> None:
        sections = {
            "kube_pod_resources_v1": cluster_deployment.pod_resources,
            "kube_memory_resources_v1": cluster_deployment.memory_resources,
            "kube_deployment_info_v1": cluster_deployment.info,
            "kube_deployment_conditions_v1": cluster_deployment.conditions,
        }
        _write_sections(sections)

    for deployment in api_deployments:
        with ConditionalPiggybackSection(f"deployment_{deployment.name(prepend_namespace=True)}"):
            output_sections(deployment)


def output_pods_api_sections(api_pods: Sequence[Pod]) -> None:
    def output_sections(cluster_pod: Pod) -> None:
        sections = {
            "kube_cpu_resources_v1": cluster_pod.cpu_resources,
            "k8s_pod_conditions_v1": cluster_pod.conditions,
            "kube_pod_containers_v1": cluster_pod.containers_infos,
            "kube_start_time_v1": cluster_pod.start_time,
            "kube_memory_resources_v1": cluster_pod.memory_resources,
            "kube_pod_lifecycle_v1": cluster_pod.lifecycle_phase,
        }
        _write_sections(sections)

    for pod in api_pods:
        with ConditionalPiggybackSection(f"pod_{pod.name(prepend_namespace=True)}"):
            output_sections(pod)


def filter_outdated_pods(
    live_pods: Sequence[PerformancePod], uid_piggyback_mappings: Mapping[PodUID, str]
) -> Iterator[PerformancePod]:
    return (live_pod for live_pod in live_pods if live_pod.uid in uid_piggyback_mappings)


def cluster_performance_sections(pods: List[PerformancePod]) -> None:
    sections = [
        (SectionName("memory"), section.Memory, ("memory_usage_bytes", "memory_swap")),
    ]
    for section_name, section_model, metrics in sections:
        section_containers = _performance_section_containers(
            container_model=_extract_container_model(section_model),
            containers=[container for pod in pods for container in pod.containers],
            metrics=metrics,
        )
        write_performance_section(
            section_name,
            section_model,
            section_containers,
        )


def node_performance_sections(pods: List[PerformancePod]) -> None:
    """Write node sections based on collected performance metrics"""
    sections = [
        (SectionName("memory"), section.Memory, ("memory_usage_bytes", "memory_swap")),
    ]
    for section_name, section_model, metrics in sections:
        section_containers = _performance_section_containers(
            container_model=_extract_container_model(section_model),
            containers=[container for pod in pods for container in pod.containers],
            metrics=metrics,
        )
        write_performance_section(
            section_name,
            section_model,
            section_containers,
        )


def deployment_performance_sections(pods: List[PerformancePod]) -> None:
    """Write deployment sections based on collected performance metrics"""
    sections = [
        (SectionName("memory"), section.Memory, ("memory_usage_bytes", "memory_swap")),
    ]
    for section_name, section_model, metrics in sections:
        section_containers = _performance_section_containers(
            container_model=_extract_container_model(section_model),
            containers=[container for pod in pods for container in pod.containers],
            metrics=metrics,
        )
        write_performance_section(
            section_name,
            section_model,
            section_containers,
        )


def pod_performance_sections(containers: Sequence[PerformanceContainer]) -> None:
    """Write pod sections based on collected performance metrics"""
    sections = [
        (SectionName("cpu_usage_total"), section.CpuUsage, ("cpu_usage_seconds_total",)),
        (SectionName("memory"), section.Memory, ("memory_usage_bytes", "memory_swap")),
    ]
    for section_name, section_model, metrics in sections:
        section_containers = _performance_section_containers(
            container_model=_extract_container_model(section_model),
            containers=containers,
            metrics=metrics,
        )
        write_performance_section(section_name, section_model, section_containers)


def write_performance_section(
    section_name: SectionName,
    section_model: Type[BaseModel],
    section_containers: Sequence[BaseModel],
) -> None:
    with SectionWriter(f"k8s_live_{section_name}_v1") as writer:
        writer.append(section_model(containers=section_containers).json())


def _performance_section_containers(
    container_model: Type[BaseModel],
    containers: Sequence[PerformanceContainer],
    metrics: Iterable[str],
) -> Sequence[BaseModel]:
    section_containers = []
    for container in containers:
        section_containers.append(
            container_model(
                name=section.ContainerName(container.name),
                **{
                    metric: container.metrics[MetricName(metric)]
                    for metric in metrics
                    if metric in container.metrics
                },
            )
        )
    return section_containers


def _extract_container_model(section_model: Type[BaseModel]) -> Type[BaseModel]:
    """Retrieve the pydantic BaseModel type of the containers' included in the overall section model

    Examples:
       >>> _extract_container_model(section.Memory)
       <class 'cmk.special_agents.utils_kubernetes.schemata.section.ContainerMemory'>
    """

    section_fields = section_model.__fields__
    if "containers" not in section_fields:
        raise DefinitionError("Performance return section should be a sequence of containers")
    return section_fields["containers"].type_


class DefinitionError(Exception):
    pass


class SetupError(Exception):
    pass


def collect_metrics_from_cluster_agent(
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


def group_metrics_by_containers(
    performance_metrics: Sequence[Mapping[str, str]]
) -> Sequence[PerformanceContainer]:
    containers: Dict[section.ContainerName, Dict[MetricName, section.PerformanceMetric]] = {}
    container_pod_uid_mappings: Dict[section.ContainerName, PodUID] = {}
    for performance_metric in performance_metrics:
        if (name := performance_metric["container_name"]) not in container_pod_uid_mappings:
            container_pod_uid_mappings[section.ContainerName(name)] = PodUID(
                performance_metric["pod_uid"]
            )

        container_metrics = containers.setdefault(section.ContainerName(name), {})
        try:
            metric_value, timestamp = performance_metric["metric_value_string"].split(" ")
            metric_timestamp = int(timestamp)
        except ValueError:
            metric_value = performance_metric["metric_value_string"]
            metric_timestamp = int(time.time())
        metric_name = performance_metric["metric_name"].replace("container_", "", 1)
        container_metrics[MetricName(metric_name)] = section.PerformanceMetric(
            value=float(metric_value), timestamp=metric_timestamp
        )

    return [
        PerformanceContainer(name=name, metrics=metrics, pod_uid=container_pod_uid_mappings[name])
        for name, metrics in containers.items()
    ]


def group_containers_by_pods(
    performance_containers: Sequence[PerformanceContainer],
) -> Mapping[PodUID, PerformancePod]:
    parsed_pods: Dict[PodUID, List[PerformanceContainer]] = {}
    for container in performance_containers:
        pod_containers = parsed_pods.setdefault(container.pod_uid, [])
        pod_containers.append(container)
    return {
        pod_uid: PerformancePod(uid=pod_uid, containers=containers)
        for pod_uid, containers in parsed_pods.items()
    }


def map_uid_to_piggyback_host_name(api_pods: Sequence[Pod]) -> Mapping[PodUID, str]:
    return {pod.uid: pod.name(prepend_namespace=True) for pod in api_pods}


def make_api_client(arguments: argparse.Namespace) -> client.ApiClient:
    config = client.Configuration()

    host = arguments.api_server_endpoint
    config.host = host
    if arguments.token:
        config.api_key_prefix["authorization"] = "Bearer"
        config.api_key["authorization"] = arguments.token

    if arguments.verify_cert:
        config.verify_ssl = False
    else:
        config.ssl_ca_cert = os.environ.get("REQUESTS_CA_BUNDLE")

    return client.ApiClient(config)


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

            # Sections based on API server
            output_cluster_api_sections(cluster)
            output_nodes_api_sections(cluster.nodes())
            output_deployments_api_sections(cluster.deployments())
            output_pods_api_sections(cluster.pods())  # TODO: make more explicit

            # Sections based on cluster agent live data
            performance_metrics = collect_metrics_from_cluster_agent(
                arguments.cluster_agent_endpoint, arguments.verify_cert
            )

            performance_containers = group_metrics_by_containers(performance_metrics)
            performance_pods = group_containers_by_pods(performance_containers)
            uid_piggyback_mappings = map_uid_to_piggyback_host_name(cluster.pods())

            for pod in filter_outdated_pods(
                list(performance_pods.values()), uid_piggyback_mappings
            ):
                with ConditionalPiggybackSection(f"pod_{uid_piggyback_mappings[pod.uid]}"):
                    pod_performance_sections(pod.containers)

            for node in cluster.nodes():
                with ConditionalPiggybackSection(f"node_{node.name}"):
                    node_performance_sections(
                        [
                            performance_pods[pod.uid]
                            for pod in node.pods(phase=api.Phase.RUNNING)
                            if pod.uid in performance_pods
                        ]
                    )

            for deployment in cluster.deployments():
                with ConditionalPiggybackSection(
                    f"deployment_{deployment.name(prepend_namespace=True)}"
                ):
                    deployment_performance_sections(
                        [
                            performance_pods[pod.uid]
                            for pod in deployment.pods(phase=api.Phase.RUNNING)
                            if pod.uid in performance_pods
                        ]
                    )

            with ConditionalPiggybackSection("cluster_kube"):  # TODO: make name configurable
                cluster_performance_sections(
                    [
                        performance_pods[pod.uid]
                        for pod in cluster.pods(phase=api.Phase.RUNNING)
                        if pod.uid in performance_pods
                    ]
                )

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
