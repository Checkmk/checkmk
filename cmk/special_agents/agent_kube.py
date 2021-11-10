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
from collections import Counter, defaultdict
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
MetricValue = NewType("MetricValue", float)
PodUID = NewType("PodUID", str)


class LivePod(NamedTuple):
    uid: PodUID
    containers: List[LiveContainer]


class LiveContainer(NamedTuple):
    name: str
    metrics: Dict[MetricName, MetricValue]


class Resources(BaseModel):
    limit: float
    requests: float


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
    p.add_argument("--port", type=int, default=None, help="Port to connect to")
    p.add_argument("--token", required=True, help="Token for that user")
    p.add_argument(
        "--api-server-endpoint", required=True, help="API server endpoint for Kubernetes API calls"
    )
    p.add_argument(
        "--cluster-agent-endpoint",
        required=True,
        help="Endpoint to query metrics from Kubernetes cluster agent",
    )
    p.add_argument(
        "--path-prefix",
        default="",
        action=PathPrefixAction,
        help="Optional URL path prefix to prepend to Kubernetes API calls",
    )
    p.add_argument("--no-cert-check", action="store_true", help="Disable certificate verification")
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
        containers: Sequence[api.ContainerInfo],
    ) -> None:
        self.uid = PodUID(uid)
        self.metadata = metadata
        self.node = spec.node
        self.phase = status.phase
        self.status_conditions = status.conditions
        self.resources = resources
        self.containers = containers

    def name(self, prepend_namespace=False) -> str:
        if not prepend_namespace:
            return self.metadata.name

        return f"{self.metadata.namespace}_{self.metadata.name}"

    def cpu_resources(self) -> Resources:
        return Resources(
            limit=self.resources.cpu.limit,
            requests=self.resources.cpu.requests,
        )

    def memory_resources(self) -> Resources:
        return Resources(limit=self.resources.memory.limit, requests=self.resources.memory.requests)

    def conditions(self) -> section.PodConditions:
        # TODO: separate section for custom conditions
        return section.PodConditions(
            **{
                condition.type.value: section.PodCondition(
                    status=condition.status,
                    reason=condition.reason,
                    detail=condition.detail,
                )
                for condition in self.status_conditions
                if condition.type is not None
            }
        )

    def containers_infos(self) -> Optional[section.PodContainers]:
        if not self.containers:
            return None
        return section.PodContainers(containers=self.containers)


class Deployment:
    def __init__(self, metadata: api.MetaData) -> None:
        self.metadata = metadata
        self._pods: List[Pod] = []

    def name(self, prepend_namespace: bool = False) -> str:
        if not prepend_namespace:
            return self.metadata.name

        return f"{self.metadata.namespace}_{self.metadata.name}"

    def add_pod(self, pod: Pod) -> None:
        self._pods.append(pod)

    def pod_resources(self) -> section.PodResources:
        resources: DefaultDict[str, int] = defaultdict(int)
        for pod in self._pods:
            resources[pod.phase] += 1
        return section.PodResources(**resources)

    def memory_resources(self) -> Resources:
        resources: DefaultDict[str, float] = defaultdict(float)
        for pod in self._pods:
            for k, v in dict(pod.memory_resources()).items():
                resources[k] += v
        return Resources(**resources)


class Node:
    def __init__(
        self,
        metadata: api.MetaData,
        resources: Dict[str, api.NodeResources],
        control_plane: bool,
        kubelet_info: api.KubeletInfo,
    ) -> None:
        self.metadata = metadata
        self.resources = resources
        self.control_plane = control_plane
        self.kubelet_info = kubelet_info
        self._pods: List[Pod] = []

    @property
    def name(self) -> str:
        return self.metadata.name

    def append(self, pod: Pod) -> None:
        self._pods.append(pod)

    def pod_resources(self) -> section.PodResources:
        resources = {
            "capacity": self.resources["capacity"].pods,
            "allocatable": self.resources["allocatable"].pods,
        }
        resources.update(dict(Counter([pod.phase for pod in self._pods])))
        return section.PodResources(**resources)

    def kubelet(self) -> api.KubeletInfo:
        return self.kubelet_info

    def container_count(self) -> section.ContainerCount:
        result = section.ContainerCount()
        for pod in self._pods:
            for container in pod.containers:
                if container.state.type == "running":
                    result.running += 1
                elif container.state.type == "waiting":
                    result.waiting += 1
                else:
                    result.terminated += 1

        return result


class Cluster:
    @classmethod
    def from_api_server(cls, api_server: api.API) -> Cluster:
        cluster_details = api_server.cluster_details()

        cluster = cls(cluster_details=cluster_details)
        for node_api in api_server.nodes():
            node = Node(
                node_api.metadata, node_api.resources, node_api.control_plane, node_api.kubelet_info
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
            cluster.add_deployment(Deployment(deployment.metadata), deployment.pods)

        return cluster

    def __init__(self, *, cluster_details: Optional[api.ClusterInfo] = None) -> None:
        self._nodes: Dict[str, Node] = {}
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
        try:
            node = self._nodes[pod.node]
        except KeyError:
            raise KeyError(f"Node {pod.node} of {pod.name} was not listed in the API")
        node.append(pod)
        self._pods[pod.uid] = pod

    def pod_resources(self) -> section.PodResources:
        resources: DefaultDict[str, int] = defaultdict(int)
        for node in self._nodes.values():
            for k, v in dict(node.pod_resources()).items():
                resources[k] += v
        return section.PodResources(**resources)

    def pods(self) -> Sequence[Pod]:
        return list(self._pods.values())

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
        "k8s_pods_resources": cluster.pod_resources,
        "k8s_node_count_v1": cluster.node_count,
        "k8s_cluster_details_v1": cluster.cluster_details,
    }
    _write_sections(sections)


def output_nodes_api_sections(api_nodes: Sequence[Node]) -> None:
    def output_sections(cluster_node: Node) -> None:
        sections = {
            "k8s_node_container_count_v1": cluster_node.container_count,
            "k8s_node_kubelet_v1": cluster_node.kubelet,
            "k8s_node_pods_resources_v1": cluster_node.pod_resources,
        }
        _write_sections(sections)

    for node in api_nodes:
        with ConditionalPiggybackSection(node.name):
            output_sections(node)


def output_deployments_api_sections(api_deployments: Sequence[Deployment]) -> None:
    def output_sections(cluster_deployment: Deployment) -> None:
        sections = {
            "k8s_deployment_pods_resources_v1": cluster_deployment.pod_resources,
            "k8s_memory_resources_v1": cluster_deployment.memory_resources,
        }
        _write_sections(sections)

    for deployment in api_deployments:
        with ConditionalPiggybackSection(deployment.name(prepend_namespace=True)):
            output_sections(deployment)


def output_pods_api_sections(api_pods: Sequence[Pod]) -> None:
    def output_sections(cluster_pod: Pod) -> None:
        sections = {
            "k8s_cpu_resources": cluster_pod.cpu_resources,
            "k8s_pod_condition_v1": cluster_pod.conditions,
            "k8s_pod_containers_v1": cluster_pod.containers_infos,
        }
        _write_sections(sections)

    for pod in api_pods:
        with ConditionalPiggybackSection(pod.name(prepend_namespace=True)):
            output_sections(pod)


def filter_outdated_pods(
    live_pods: Sequence[LivePod], uid_piggyback_mappings: Mapping[PodUID, str]
) -> Iterator[LivePod]:
    return (live_pod for live_pod in live_pods if live_pod.uid in uid_piggyback_mappings)


def pod_checkmk_sections(containers: List[LiveContainer]) -> None:
    sections = [
        ("cpu_usage_total", section.CpuUsage, ("cpu_usage_total")),  # TODO: adjust check section
        ("cpu_load", section.CpuLoad, ("cpu_cfs_throttled_time", "cpu_load_average")),
    ]
    for section_name, section_model, metrics in sections:
        with SectionWriter(f"k8s_live_{section_name}_v1") as writer:
            containers_sections = {}
            for container in containers:
                try:
                    containers_sections[container.name] = section_model(
                        **{
                            metric: container.metrics[MetricName(metric)]
                            for metric in metrics
                            if metric in container.metrics
                        }
                    ).json()
                except ValueError:  # TODO: decide if additional conditions are necessary
                    continue

            writer.append(containers_sections)


class SetupError(Exception):
    pass


def collect_metrics_from_cluster_agent(cluster_url: str) -> List[str]:
    cluster_resp = requests.get(f"{cluster_url}/kmetrics")  # TODO: certificate validation
    if cluster_resp.status_code != 200:
        raise SetupError("Checkmk cannot make a connection to the k8 cluster agent")

    if not cluster_resp.content:
        raise SetupError("Worker nodes")

    return cluster_resp.content.decode("utf-8").split("\n")


def group_metrics_by_pods(nodes_metrics: List[str]) -> Sequence[LivePod]:
    def group_by_pods(containers_collection) -> List[LivePod]:
        parsed_pods: Dict[str, List[LiveContainer]] = {}

        for container_name, container_info in containers_collection.items():
            pod_containers = parsed_pods.setdefault(container_info["pod_uid"], [])
            pod_containers.append(
                LiveContainer(
                    name=container_name,
                    metrics={
                        MetricName(metric["name"]): MetricValue(metric["value"])
                        for metric in container_info["metrics"].values()
                    },
                )
            )
        return [
            LivePod(uid=PodUID(pod_uid), containers=containers)
            for pod_uid, containers in parsed_pods.items()
        ]

    pods: List[LivePod] = []
    for collection in nodes_metrics:
        try:
            pods.extend(group_by_pods(json.loads(collection)["containers"]))
        except (KeyError, json.JSONDecodeError):
            continue
    return pods


def map_uid_to_piggyback_host_name(api_pods: Sequence[Pod]) -> Mapping[PodUID, str]:
    return {pod.uid: pod.name(prepend_namespace=True) for pod in api_pods}


def make_api_client(arguments: argparse.Namespace) -> client.ApiClient:
    config = client.Configuration()

    host = arguments.api_server_endpoint
    if arguments.port is not None:
        host = "%s:%s" % (host, arguments.port)
    if arguments.path_prefix:
        host = "%s%s" % (host, arguments.path_prefix)
    config.host = host
    config.api_key_prefix["authorization"] = "Bearer"
    config.api_key["authorization"] = arguments.token

    if arguments.no_cert_check:
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
            live_metrics = collect_metrics_from_cluster_agent(arguments.cluster_agent_endpoint)
            live_pods = group_metrics_by_pods(live_metrics)
            uid_piggyback_mappings = map_uid_to_piggyback_host_name(cluster.pods())

            for pod in filter_outdated_pods(live_pods, uid_piggyback_mappings):
                with ConditionalPiggybackSection(uid_piggyback_mappings[pod.uid]):
                    pod_checkmk_sections(pod.containers)

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
