#!/usr/bin/env python3
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
import unittest
import uuid
from typing import Callable, Mapping, Sequence

import pytest
import pytest_mock
from pydantic_factories import ModelFactory, Use

# pylint: disable=comparison-with-callable,redefined-outer-name
from tests.unit.cmk.special_agents.agent_kube.factory import (
    api_to_agent_daemonset,
    api_to_agent_statefulset,
    APIDaemonSetFactory,
    APIStatefulSetFactory,
    MetaDataFactory,
    NodeMetaDataFactory,
)

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
    metadata = MetaDataFactory.build
    status = PodStatusFactory.build
    spec = _spec
    containers = _containers


# Node Factories
class KubeletInfoFactory(ModelFactory):
    __model__ = api.KubeletInfo


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
class DeploymentFactory(ModelFactory):
    __model__ = api.Deployment


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
def container_state(container_status_state) -> api.ContainerState:  # type:ignore[no-untyped-def]
    if container_status_state == api.ContainerStateType.running:
        return ContainerRunningStateFactory.build()
    if container_status_state == api.ContainerStateType.waiting:
        return ContainerWaitingStateFactory.build()
    if container_status_state == api.ContainerStateType.terminated:
        return ContainerTerminatedStateFactory.build()
    raise ValueError(f"Unknown container state: {container_status_state}")


@pytest.fixture
def container_status(  # type:ignore[no-untyped-def]
    container_state,
) -> Callable[[], api.ContainerStatus]:
    def _container_status() -> api.ContainerStatus:
        return ContainerStatusFactory.build(state=container_state)

    return _container_status


def api_to_agent_node(node: api.Node) -> agent_kube.Node:
    return agent_kube.Node(
        metadata=node.metadata,
        status=node.status,
        resources=node.resources,
        roles=node.roles,
        kubelet_info=node.kubelet_info,
    )


@pytest.fixture
def node_pods() -> int:
    return len(api.Phase)


@pytest.fixture
def cluster_nodes() -> int:
    return 3


@pytest.fixture
def cluster_daemon_sets() -> int:
    return 6


@pytest.fixture
def cluster_statefulsets() -> int:
    return 6


@pytest.fixture
def cluster(
    cluster_nodes: int,
    cluster_daemon_sets: int,
    cluster_statefulsets: int,
) -> agent_kube.Cluster:
    cluster = agent_kube.Cluster(
        excluded_node_roles=[], cluster_details=ClusterDetailsFactory.build()
    )
    for _ in range(cluster_nodes):
        node = api_to_agent_node(APINodeFactory.build())
        cluster.add_node(node)
    for _ in range(cluster_daemon_sets):
        daemonset = api_to_agent_daemonset(APIDaemonSetFactory.build())
        cluster.add_daemon_set(daemonset)
    for _ in range(cluster_statefulsets):
        statefulset = api_to_agent_statefulset(APIStatefulSetFactory.build())
        cluster.add_statefulset(statefulset)
    return cluster


def api_to_agent_cluster(
    excluded_node_roles: Sequence[str] = ("control_plane", "master"),
    pods: Sequence[api.Pod] = (),
    nodes: Sequence[api.Node] = (),
    statefulsets: Sequence[api.StatefulSet] = (),
    deployments: Sequence[api.Deployment] = (),
    daemon_sets: Sequence[api.DaemonSet] = (),
    cluster_details: api.ClusterDetails = ClusterDetailsFactory.build(),
) -> agent_kube.Cluster:
    return agent_kube.Cluster.from_api_resources(
        excluded_node_roles=excluded_node_roles or [],
        pods=pods,
        nodes=nodes,
        statefulsets=statefulsets,
        deployments=deployments,
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
def write_sections_mock(mocker: pytest_mock.MockFixture) -> unittest.mock.MagicMock:
    return mocker.patch("cmk.special_agents.agent_kube._write_sections")
