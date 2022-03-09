#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


####################################################################################
# NOTE: This is considered as a workaround file and is intended to removed
# in the future.
# Existing factories should be moved to factory.py. Fixtures should be refactored
# to delegate the build logic directly into the test.
####################################################################################


import itertools
import uuid
from typing import Callable, Dict, Iterator, Mapping, Sequence, Type

import pytest
from pydantic_factories import ModelFactory, Use

# pylint: disable=comparison-with-callable,redefined-outer-name
from tests.unit.cmk.special_agents.agent_kube.factory import MetaDataFactory

from cmk.special_agents import agent_kube
from cmk.special_agents.utils_kubernetes.schemata import api

ONE_KiB = 1024
ONE_MiB = 1024 * ONE_KiB
ONE_GiB = 1024 * ONE_MiB


# Container Factories
class ContainerRunningStateFactory(ModelFactory):
    __model__ = api.ContainerRunningState


class ContainerWaitingStateFactory(ModelFactory):
    __model__ = api.ContainerWaitingState


class ContainerTerminatedStateFactory(ModelFactory):
    __model__ = api.ContainerTerminatedState


class ContainerStatusFactory(ModelFactory):
    __model__ = api.ContainerStatus


class ContainerSpecFactory(ModelFactory):
    __model__ = api.ContainerSpec


# Pod Factories
class PodMetaDataFactory(ModelFactory):
    __model__ = api.PodMetaData

    name = Use(lambda x: str(next(x)), itertools.count(0, 1))


class PodStatusFactory(ModelFactory):
    __model__ = api.PodStatus

    phase = Use(next, itertools.cycle(api.Phase))


class PodSpecFactory(ModelFactory):
    __model__ = api.PodSpec


containers_count = 1


class APIPodFactory(ModelFactory):
    __model__ = api.Pod

    @staticmethod
    def _uid() -> api.PodUID:
        return api.PodUID(str(uuid.uuid4()))

    @staticmethod
    def _spec() -> api.PodSpec:
        return PodSpecFactory.build(containers=ContainerSpecFactory.batch(containers_count))

    @staticmethod
    def _containers() -> Mapping[str, api.ContainerStatus]:
        return {
            container.name: container
            for container in ContainerStatusFactory.batch(containers_count)
        }

    uid = _uid
    metadata = PodMetaDataFactory.build
    status = PodStatusFactory.build
    spec = _spec
    containers = _containers


# Node Factories
class KubeletInfoFactory(ModelFactory):
    __model__ = api.KubeletInfo


class NodeMetaDataFactory(ModelFactory):
    __model__ = api.NodeMetaData


class NodeResourcesFactory(ModelFactory):
    __model__ = api.NodeResources


NPD_NODE_CONDITION_TYPES = [
    "KernelDeadlock",
    "ReadonlyFilesystem",
    "FrequentKubeletRestart",
    "FrequentDockerRestart",
    "FrequentContainerdRestart",
]


class NodeConditionFactory(ModelFactory):
    __model__ = api.NodeCondition

    type_ = Use(
        next, itertools.cycle(agent_kube.NATIVE_NODE_CONDITION_TYPES + NPD_NODE_CONDITION_TYPES)
    )


class NodeStatusFactory(ModelFactory):
    __model__ = api.NodeStatus

    conditions = Use(
        NodeConditionFactory.batch,
        size=len(agent_kube.NATIVE_NODE_CONDITION_TYPES) + len(NPD_NODE_CONDITION_TYPES),
    )


@pytest.fixture
def node_condition_status() -> api.NodeConditionStatus:
    return api.NodeConditionStatus.TRUE


@pytest.fixture
def node_status(node_condition_status: api.NodeConditionStatus) -> api.NodeStatus:
    return NodeStatusFactory.build(
        conditions=NodeConditionFactory.batch(
            len(agent_kube.NATIVE_NODE_CONDITION_TYPES) + len(NPD_NODE_CONDITION_TYPES),
            status=node_condition_status,
        )
    )


class APINodeFactory(ModelFactory):
    __model__ = api.Node

    @staticmethod
    def _resources() -> dict[str, api.NodeResources]:
        return {
            "capacity": NodeResourcesFactory.build(),
            "allocatable": NodeResourcesFactory.build(),
        }

    metadata = NodeMetaDataFactory.build
    status = NodeStatusFactory.build
    control_plane = False
    resources = _resources
    kubelet_info = KubeletInfoFactory.build


# DaemonSet Factories
class DaemonSetSpecFactory(ModelFactory):
    __model__ = api.DaemonSetSpec


# StatefulSet Factories
class StatefulSetSpecFactory(ModelFactory):
    __model__ = api.StatefulSetSpec


# Cluster Factories
class ClusterDetailsFactory(ModelFactory):
    __model__ = api.ClusterDetails


# Deployment Factories
class DeploymentSpecFactory(ModelFactory):
    __model__ = api.DeploymentSpec


class DeploymentStatusFactory(ModelFactory):
    __model__ = api.DeploymentStatus


# DaemonSet Factories


class DaemonSetStatusFactory(ModelFactory):
    __model__ = api.DaemonSetStatus


# StatefulSet Factories


class StatefulSetStatusFactory(ModelFactory):
    __model__ = api.StatefulSetStatus


# Container Status Fixtures
@pytest.fixture
def container_status_state() -> api.ContainerStateType:
    return api.ContainerStateType.running


@pytest.fixture
def container_state(container_status_state) -> api.ContainerState:
    if container_status_state == api.ContainerStateType.running:
        return ContainerRunningStateFactory.build()
    if container_status_state == api.ContainerStateType.waiting:
        return ContainerWaitingStateFactory.build()
    if container_status_state == api.ContainerStateType.terminated:
        return ContainerTerminatedStateFactory.build()
    raise ValueError(f"Unknown container state: {container_status_state}")


@pytest.fixture
def container_status(container_state) -> Callable[[], api.ContainerStatus]:
    def _container_status() -> api.ContainerStatus:
        return ContainerStatusFactory.build(state=container_state)

    return _container_status


# Container Fixtures
@pytest.fixture
def pod_containers_count() -> int:
    return 1


@pytest.fixture
def container_limit_cpu() -> float:
    return 2.0


@pytest.fixture
def container_request_cpu() -> float:
    return 1.0


@pytest.fixture
def container_limit_memory() -> float:
    return 2.0 * ONE_MiB


@pytest.fixture
def container_request_memory() -> float:
    return 1.0 * ONE_MiB


@pytest.fixture
def container_resources_requirements(
    container_request_cpu: float,
    container_limit_cpu: float,
    container_request_memory: float,
    container_limit_memory: float,
) -> api.ContainerResources:
    return api.ContainerResources(
        limits=api.ResourcesRequirements(
            memory=container_limit_memory,
            cpu=container_limit_cpu,
        ),
        requests=api.ResourcesRequirements(
            memory=container_request_memory,
            cpu=container_request_cpu,
        ),
    )


@pytest.fixture
def container_spec(container_resources_requirements: api.ContainerResources) -> api.ContainerSpec:
    return ContainerSpecFactory.build(resources=container_resources_requirements)


@pytest.fixture
def pod_spec(container_spec: api.ContainerSpec, pod_containers_count: int) -> api.PodSpec:
    return PodSpecFactory.build(
        node=None, containers=[container_spec for _ in range(pod_containers_count)]
    )


@pytest.fixture
def node_allocatable_cpu() -> float:
    return 6.0


@pytest.fixture
def node_allocatable_memory() -> float:
    return 7.0 * ONE_GiB


@pytest.fixture
def node_allocatable_pods() -> int:
    return 1


@pytest.fixture
def node_capacity_pods() -> int:
    return 1


@pytest.fixture
def node_is_control_plane() -> bool:
    return False


@pytest.fixture
def node_resources_builder(
    node_allocatable_cpu: float,
    node_allocatable_memory: float,
    node_allocatable_pods: int,
    node_capacity_pods: int,
) -> Callable[[], Dict[str, api.NodeResources]]:
    def _node_resources_builder() -> Dict[str, api.NodeResources]:
        return {
            "capacity": NodeResourcesFactory.build(pods=node_capacity_pods),
            "allocatable": NodeResourcesFactory().build(
                cpu=node_allocatable_cpu, memory=node_allocatable_memory, pods=node_allocatable_pods
            ),
        }

    return _node_resources_builder


@pytest.fixture
def new_node(
    node_resources_builder: Callable[[], Dict[str, api.NodeResources]],
    node_status: api.NodeStatus,
    node_is_control_plane: bool,
) -> Callable[[], agent_kube.Node]:
    def _new_node() -> agent_kube.Node:
        return agent_kube.Node(
            metadata=NodeMetaDataFactory.build(),
            status=node_status,
            resources=node_resources_builder(),
            roles=["control_plane"] if node_is_control_plane else [],
            kubelet_info=KubeletInfoFactory.build(),
        )

    return _new_node


def api_to_agent_node(node: api.Node) -> agent_kube.Node:
    return agent_kube.Node(
        metadata=node.metadata,
        status=node.status,
        resources=node.resources,
        roles=["worker"],
        kubelet_info=node.kubelet_info,
    )


@pytest.fixture
def node(
    new_node: Callable[[], agent_kube.Node], node_pods: int, new_pod: Callable[[], agent_kube.Pod]
) -> agent_kube.Node:
    node = new_node()
    for _ in range(node_pods):
        node.add_pod(new_pod())
    return node


@pytest.fixture
def pod_metadata() -> api.PodMetaData:
    return PodMetaDataFactory.build()


@pytest.fixture
def phases() -> Type[api.Phase]:
    return api.Phase


@pytest.fixture
def phase_generator(phases: Type[api.Phase]) -> Callable[[], Iterator[api.Phase]]:
    def _phase_generator() -> Iterator[api.Phase]:
        yield from itertools.cycle(phases)

    return _phase_generator


@pytest.fixture
def new_pod(
    pod_metadata: api.PodMetaData,
    phase_generator: Callable[[], Iterator[api.Phase]],
    pod_spec: api.PodSpec,
    container_status: Callable[[], api.ContainerStatus],
    pod_containers_count: int,
) -> Callable[[], agent_kube.Pod]:
    phases = phase_generator()
    containers = [container_status() for _ in range(pod_containers_count)]

    def _new_pod() -> agent_kube.Pod:
        pod_status = PodStatusFactory.build()
        pod_status.phase = next(phases)
        return agent_kube.Pod(
            uid=api.PodUID(str(uuid.uuid4())),
            metadata=pod_metadata,
            status=pod_status,
            spec=pod_spec,
            containers={container.name: container for container in containers},
            init_containers={},
        )

    return _new_pod


@pytest.fixture
def pod(new_pod: Callable[[], agent_kube.Pod]) -> agent_kube.Pod:
    return new_pod()


@pytest.fixture
def node_pods() -> int:
    return len(api.Phase)


@pytest.fixture
def daemonset_spec() -> api.DaemonSetSpec:
    return DaemonSetSpecFactory.build()


@pytest.fixture
def new_daemon_set(daemonset_spec: api.DaemonSetSpec) -> Callable[[], agent_kube.DaemonSet]:
    def _new_daemon_set() -> agent_kube.DaemonSet:
        return agent_kube.DaemonSet(
            metadata=MetaDataFactory.build(),
            spec=daemonset_spec,
            status=DaemonSetStatusFactory.build(),
        )

    return _new_daemon_set


@pytest.fixture
def daemon_set_pods() -> int:
    return len(api.Phase)


@pytest.fixture
def daemon_set(
    new_daemon_set: Callable[[], agent_kube.DaemonSet],
    daemon_set_pods: int,
    new_pod: Callable[[], agent_kube.Pod],
) -> agent_kube.DaemonSet:
    daemon_set = new_daemon_set()
    for _ in range(daemon_set_pods):
        daemon_set.add_pod(new_pod())
    return daemon_set


@pytest.fixture
def statefulset_spec() -> api.StatefulSetSpec:
    return StatefulSetSpecFactory.build()


@pytest.fixture
def new_statefulset(statefulset_spec) -> Callable[[], agent_kube.StatefulSet]:
    def _new_statefulset() -> agent_kube.StatefulSet:
        return agent_kube.StatefulSet(
            metadata=MetaDataFactory.build(),
            spec=statefulset_spec,
            status=StatefulSetStatusFactory.build(),
        )

    return _new_statefulset


@pytest.fixture
def statefulset_pods() -> int:
    return len(api.Phase)


@pytest.fixture
def statefulset(
    new_statefulset: Callable[[], agent_kube.StatefulSet],
    statefulset_pods: int,
    new_pod: Callable[[], agent_kube.Pod],
) -> agent_kube.StatefulSet:
    statefulset = new_statefulset()
    for _ in range(statefulset_pods):
        statefulset.add_pod(new_pod())
    return statefulset


@pytest.fixture
def cluster_nodes() -> int:
    return 3


@pytest.fixture
def deployment_pods() -> int:
    return len(api.Phase)


@pytest.fixture
def deployment_spec() -> api.DeploymentSpec:
    return DeploymentSpecFactory.build()


@pytest.fixture
def deployment_status() -> api.DeploymentStatus:
    return DeploymentStatusFactory.build()


@pytest.fixture
def api_deployment(
    deployment_spec: api.DeploymentSpec, deployment_status: api.DeploymentStatus
) -> api.Deployment:
    class DeploymentFactory(ModelFactory):
        __model__ = api.Deployment

    return DeploymentFactory.build(spec=deployment_spec, status=deployment_status)


@pytest.fixture
def new_deployment(
    api_deployment: api.Deployment,
) -> Callable[[], agent_kube.Deployment]:
    def _new_deployment() -> agent_kube.Deployment:
        return agent_kube.Deployment(
            metadata=api_deployment.metadata,
            spec=api_deployment.spec,
            status=api_deployment.status,
        )

    return _new_deployment


@pytest.fixture
def deployment(
    new_deployment: Callable[[], agent_kube.Deployment],
    deployment_pods: int,
    new_pod: Callable[[], agent_kube.Pod],
) -> agent_kube.Deployment:
    deployment = new_deployment()
    for _ in range(deployment_pods):
        deployment.add_pod(new_pod())
    return deployment


@pytest.fixture
def cluster_daemon_sets() -> int:
    return 6


@pytest.fixture
def cluster_statefulsets() -> int:
    return 6


@pytest.fixture
def cluster_details() -> api.ClusterDetails:
    return ClusterDetailsFactory.build()


@pytest.fixture
def cluster(
    new_node: Callable[[], agent_kube.Node],
    new_daemon_set: Callable[[], agent_kube.DaemonSet],
    new_statefulset: Callable[[], agent_kube.StatefulSet],
    cluster_nodes: int,
    cluster_daemon_sets: int,
    cluster_statefulsets: int,
    cluster_details: api.ClusterDetails,
) -> agent_kube.Cluster:
    cluster = agent_kube.Cluster(excluded_node_roles=[], cluster_details=cluster_details)
    for _ in range(cluster_nodes):
        cluster.add_node(new_node())
    for _ in range(cluster_daemon_sets):
        cluster.add_daemon_set(new_daemon_set())
    for _ in range(cluster_statefulsets):
        cluster.add_statefulset(new_statefulset())
    return cluster


def api_to_agent_cluster(  # pylint: disable=dangerous-default-value
    excluded_node_roles: Sequence[str] = ["control_plane", "master"],
    pods: Sequence[api.Pod] = [],
    nodes: Sequence[api.Node] = [],
    statefulsets: Sequence[api.StatefulSet] = [],
    deployments: Sequence[api.Deployment] = [],
    cron_jobs: Sequence[api.CronJob] = [],
    daemon_sets: Sequence[api.DaemonSet] = [],
    cluster_details: api.ClusterDetails = ClusterDetailsFactory.build(),
) -> agent_kube.Cluster:
    return agent_kube.Cluster.from_api_resources(
        excluded_node_roles=excluded_node_roles or [],
        pods=pods,
        nodes=nodes,
        statefulsets=statefulsets,
        deployments=deployments,
        cron_jobs=cron_jobs,
        daemon_sets=daemon_sets,
        cluster_details=cluster_details,
    )


@pytest.fixture
def nodes_api_sections() -> Sequence[str]:
    return [
        "kube_node_container_count_v1",
        "kube_node_kubelet_v1",
        "kube_pod_resources_v1",
        "kube_allocatable_pods_v1",
        "kube_node_info_v1",
        "kube_cpu_resources_v1",
        "kube_memory_resources_v1",
        "kube_allocatable_cpu_resource_v1",
        "kube_allocatable_memory_resource_v1",
        "kube_node_conditions_v1",
        "kube_node_custom_conditions_v1",
    ]


@pytest.fixture
def cluster_api_sections() -> Sequence[str]:
    return [
        "kube_pod_resources_v1",
        "kube_allocatable_pods_v1",
        "kube_node_count_v1",
        "kube_cluster_details_v1",
        "kube_memory_resources_v1",
        "kube_cpu_resources_v1",
        "kube_allocatable_memory_resource_v1",
        "kube_allocatable_cpu_resource_v1",
        "kube_cluster_info_v1",
        "kube_collector_daemons_v1",
    ]


@pytest.fixture
def deployments_api_sections() -> Sequence[str]:
    return [
        "kube_pod_resources_v1",
        "kube_memory_resources_v1",
        "kube_deployment_info_v1",
        "kube_deployment_conditions_v1",
        "kube_cpu_resources_v1",
        "kube_update_strategy_v1",
        "kube_deployment_replicas_v1",
    ]


@pytest.fixture
def daemon_sets_api_sections() -> Sequence[str]:
    return [
        "kube_pod_resources_v1",
        "kube_memory_resources_v1",
        "kube_cpu_resources_v1",
        "kube_daemonset_info_v1",
        "kube_update_strategy_v1",
        "kube_daemonset_replicas_v1",
    ]


@pytest.fixture
def statefulsets_api_sections() -> Sequence[str]:
    return [
        "kube_pod_resources_v1",
        "kube_memory_resources_v1",
        "kube_cpu_resources_v1",
        "kube_statefulset_info_v1",
        "kube_update_strategy_v1",
        "kube_statefulset_replicas_v1",
    ]


@pytest.fixture
def write_sections_mock(mocker):
    return mocker.patch("cmk.special_agents.agent_kube._write_sections")
