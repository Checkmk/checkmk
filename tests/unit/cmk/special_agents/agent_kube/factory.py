#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import itertools
from typing import Iterator, Sequence

from pydantic_factories import ModelFactory, Use

from cmk.special_agents import agent_kube as agent
from cmk.special_agents.utils_kubernetes import performance
from cmk.special_agents.utils_kubernetes.schemata import api


# Container related Factories
class ContainerRunningStateFactory(ModelFactory):
    __model__ = api.ContainerRunningState


class ContainerWaitingStateFactory(ModelFactory):
    __model__ = api.ContainerWaitingState


class ContainerTerminatedStateFactory(ModelFactory):
    __model__ = api.ContainerTerminatedState


def create_container_state(
    state: api.ContainerStateType, **kwargs: dict[str, object]
) -> api.ContainerState:
    state_factory = {
        api.ContainerStateType.running: ContainerRunningStateFactory.build,
        api.ContainerStateType.waiting: ContainerWaitingStateFactory.build,
        api.ContainerStateType.terminated: ContainerTerminatedStateFactory.build,
    }[state]
    return state_factory()


class ContainerStatusFactory(ModelFactory):
    __model__ = api.ContainerStatus


class ContainerSpecFactory(ModelFactory):
    __model__ = api.ContainerSpec


class ContainerResourcesFactory(ModelFactory):
    __model__ = api.ContainerResources


# General Factories


class MetaDataFactory(ModelFactory[api.MetaData[str]]):
    __model__ = api.MetaData[str]


# Pod related Factories


class PodSpecFactory(ModelFactory):
    __model__ = api.PodSpec


class PodStatusFactory(ModelFactory):
    __model__ = api.PodStatus


class APIPodFactory(ModelFactory):
    __model__ = api.Pod


class APIControllerFactory(ModelFactory):
    __model__ = api.Controller


def pod_phase_generator() -> Iterator[api.Phase]:
    yield from itertools.cycle(api.Phase)


# Deployment related Factories


class DeploymentStatusFactory(ModelFactory):
    __model__ = api.DeploymentStatus


class APIDeploymentFactory(ModelFactory):
    __model__ = api.Deployment


def api_to_agent_deployment(
    api_deployment: api.Deployment, pods: Sequence[api.Pod] = ()
) -> agent.Deployment:
    return agent.Deployment(
        metadata=api_deployment.metadata,
        spec=api_deployment.spec,
        status=api_deployment.status,
        pods=pods,
    )


# DaemonSet related Factories


class APIDaemonSetFactory(ModelFactory):
    __model__ = api.DaemonSet


def api_to_agent_daemonset(
    api_daemonset: api.DaemonSet, pods: Sequence[api.Pod] = ()
) -> agent.DaemonSet:
    return agent.DaemonSet(
        metadata=api_daemonset.metadata,
        spec=api_daemonset.spec,
        status=api_daemonset.status,
        pods=pods,
    )


# StatefulSet related Factories


class APIStatefulSetFactory(ModelFactory):
    __model__ = api.StatefulSet


def api_to_agent_statefulset(
    api_statefulset: api.StatefulSet, pods: Sequence[api.Pod] = ()
) -> agent.StatefulSet:
    return agent.StatefulSet(
        metadata=api_statefulset.metadata,
        spec=api_statefulset.spec,
        status=api_statefulset.status,
        pods=pods,
    )


# Namespace & Resource Quota related Factories


class NamespaceMetaDataFactory(ModelFactory):
    __model__ = api.MetaDataNoNamespace[api.NamespaceName]


class APIResourceQuotaFactory(ModelFactory):
    __model__ = api.ResourceQuota


# Performance related Factories


class PerformancePodFactory(ModelFactory):
    __model__ = performance.PerformancePod


# Node related Factories


class NodeMetaDataFactory(ModelFactory):
    __model__ = api.MetaDataNoNamespace[api.NodeName]


class NodeResourcesFactory(ModelFactory):
    __model__ = api.NodeResources


class APINodeFactory(ModelFactory):
    __model__ = api.Node


NPD_NODE_CONDITION_TYPES = [
    "KernelDeadlock",
    "ReadonlyFilesystem",
    "FrequentKubeletRestart",
    "FrequentDockerRestart",
    "FrequentContainerdRestart",
]


class NodeConditionFactory(ModelFactory):
    __model__ = api.NodeCondition

    type_ = Use(next, itertools.cycle(agent.NATIVE_NODE_CONDITION_TYPES + NPD_NODE_CONDITION_TYPES))


class NodeStatusFactory(ModelFactory):
    __model__ = api.NodeStatus

    conditions = Use(
        NodeConditionFactory.batch,
        size=len(agent.NATIVE_NODE_CONDITION_TYPES) + len(NPD_NODE_CONDITION_TYPES),
    )


def node_status(node_condition_status: api.NodeConditionStatus) -> api.NodeStatus:
    return NodeStatusFactory.build(
        conditions=NodeConditionFactory.batch(
            len(agent.NATIVE_NODE_CONDITION_TYPES) + len(NPD_NODE_CONDITION_TYPES),
            status=node_condition_status,
        )
    )


def api_to_agent_node(node: api.Node, pods: Sequence[api.Pod] = ()) -> agent.Node:
    return agent.Node(
        metadata=node.metadata,
        status=node.status,
        resources=node.resources,
        roles=node.roles,
        kubelet_info=node.kubelet_info,
        pods=pods,
    )


# Cluster related Factories


class ClusterDetailsFactory(ModelFactory):
    __model__ = api.ClusterDetails


def api_to_agent_cluster(
    excluded_node_roles: Sequence[str] = ("control_plane", "master"),
    pods: Sequence[api.Pod] = (),
    nodes: Sequence[api.Node] = (),
    statefulsets: Sequence[api.StatefulSet] = (),
    deployments: Sequence[api.Deployment] = (),
    daemon_sets: Sequence[api.DaemonSet] = (),
    cluster_details: api.ClusterDetails = ClusterDetailsFactory.build(),
) -> agent.Cluster:
    return agent.Cluster.from_api_resources(
        excluded_node_roles=excluded_node_roles or [],
        pods=pods,
        nodes=nodes,
        statefulsets=statefulsets,
        deployments=deployments,
        daemon_sets=daemon_sets,
        cluster_details=cluster_details,
    )
