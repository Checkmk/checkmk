#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import itertools
from typing import Iterator

from pydantic_factories import ModelFactory

from cmk.special_agents import agent_kube as agent
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


def api_to_agent_pod(pod: api.Pod) -> agent.Pod:
    return agent.Pod(
        uid=pod.uid,
        metadata=pod.metadata,
        status=pod.status,
        spec=pod.spec,
        containers=pod.containers,
        init_containers=pod.init_containers,
    )


# Deployment related Factories


class APIDeploymentFactory(ModelFactory):
    __model__ = api.Deployment


def api_to_agent_deployment(api_deployment: api.Deployment) -> agent.Deployment:
    return agent.Deployment(
        metadata=api_deployment.metadata,
        spec=api_deployment.spec,
        status=api_deployment.status,
    )


# DaemonSet related Factories


class APIDaemonSetFactory(ModelFactory):
    __model__ = api.DaemonSet


def api_to_agent_daemonset(api_daemonset: api.DaemonSet) -> agent.DaemonSet:
    return agent.DaemonSet(
        metadata=api_daemonset.metadata,
        spec=api_daemonset.spec,
        status=api_daemonset.status,
    )


# StatefulSet related Factories


class APIStatefulSetFactory(ModelFactory):
    __model__ = api.StatefulSet


def api_to_agent_statefulset(api_statefulset: api.StatefulSet) -> agent.StatefulSet:
    return agent.StatefulSet(
        metadata=api_statefulset.metadata,
        spec=api_statefulset.spec,
        status=api_statefulset.status,
    )


# Namespace & Resource Quota related Factories


class NamespaceMetaDataFactory(ModelFactory):
    __model__ = api.MetaDataNoNamespace[api.NamespaceName]


class APIResourceQuotaFactory(ModelFactory):
    __model__ = api.ResourceQuota


# Performance related Factories


class PerformancePodFactory(ModelFactory):
    __model__ = agent.PerformancePod


# Node related Factories


class NodeMetaDataFactory(ModelFactory):
    __model__ = api.MetaDataNoNamespace[api.NodeName]
