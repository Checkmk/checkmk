#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=comparison-with-callable,redefined-outer-name
import itertools

import pytest
from pydantic_factories import ModelFactory, Use

from cmk.special_agents import agent_kube
from cmk.special_agents.utils_kubernetes.schemata import api

ONE_KiB = 1024
ONE_MiB = 1024 * ONE_KiB
ONE_GiB = 1024 * ONE_MiB


# Pod Factories
class PodMetaDataFactory(ModelFactory):
    __model__ = api.PodMetaData


class PodStatusFactory(ModelFactory):
    __model__ = api.PodStatus


# Node Factories
class KubeletInfoFactory(ModelFactory):
    __model__ = api.KubeletInfo


class NodeMetaDataFactory(ModelFactory):
    __model__ = api.NodeMetaData


class NodeResourcesFactory(ModelFactory):
    __model__ = api.NodeResources


class NodeConditionFactory(ModelFactory):
    __model__ = api.NodeCondition

    type_ = Use(next, itertools.cycle(agent_kube.NATIVE_NODE_CONDITION_TYPES))


class NodeStatusFactory(ModelFactory):
    __model__ = api.NodeStatus

    conditions = Use(NodeConditionFactory.batch, size=len(agent_kube.NATIVE_NODE_CONDITION_TYPES))


# Container Fixtures
@pytest.fixture
def pod_containers_count():
    return 1


@pytest.fixture
def container_limit_cpu():
    return 2.0


@pytest.fixture
def container_request_cpu():
    return 1.0


@pytest.fixture
def container_limit_memory():
    return 2.0 * ONE_MiB


@pytest.fixture
def container_request_memory():
    return 1.0 * ONE_MiB


@pytest.fixture
def container_resources_requirements(
    container_request_cpu, container_limit_cpu, container_request_memory, container_limit_memory
):
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
def container_spec(container_resources_requirements):
    class ContainerSpecFactory(ModelFactory):
        __model__ = api.ContainerSpec

        resources = container_resources_requirements

    return ContainerSpecFactory.build()


@pytest.fixture
def pod_spec(container_spec, pod_containers_count):
    class PodSpecFactory(ModelFactory):
        __model__ = api.PodSpec

        containers = [container_spec for _ in range(pod_containers_count)]

    return PodSpecFactory.build()


@pytest.fixture
def node_allocatable_cpu():
    return 6.0


@pytest.fixture
def node_allocatable_memory():
    return 7.0 * ONE_GiB


@pytest.fixture
def node_resources_builder(node_allocatable_cpu, node_allocatable_memory):
    def _node_resources_builder():
        return {
            "capacity": NodeResourcesFactory.build(),
            "allocatable": NodeResourcesFactory().build(
                cpu=node_allocatable_cpu, memory=node_allocatable_memory
            ),
        }

    return _node_resources_builder


@pytest.fixture
def new_node(node_resources_builder):
    def _new_node():
        return agent_kube.Node(
            metadata=NodeMetaDataFactory.build(),
            status=NodeStatusFactory.build(),
            resources=node_resources_builder(),
            control_plane=False,
            kubelet_info=KubeletInfoFactory.build(),
        )

    return _new_node


@pytest.fixture
def node(new_node, node_pods, new_pod):
    node = new_node()
    for _ in range(node_pods):
        node.append(new_pod())
    return node


@pytest.fixture
def phases():
    return api.Phase


@pytest.fixture
def phase_generator(phases):
    def _phase_generator():
        yield from itertools.cycle(phases)

    return _phase_generator


@pytest.fixture
def new_pod(phase_generator, pod_spec):
    phases = phase_generator()

    def _new_pod():
        pod_status = PodStatusFactory.build()
        pod_status.phase = next(phases)
        return agent_kube.Pod(
            uid=api.PodUID("test-pod"),
            metadata=PodMetaDataFactory.build(),
            status=pod_status,
            spec=pod_spec,
            containers={},
            init_containers={},
        )

    return _new_pod


@pytest.fixture
def node_pods():
    return len(api.Phase)


@pytest.fixture
def cluster_nodes():
    return 3


@pytest.fixture
def cluster(new_node, cluster_nodes):
    cluster = agent_kube.Cluster()
    for _ in range(cluster_nodes):
        cluster.add_node(new_node())
    return cluster


@pytest.fixture
def nodes_api_sections():
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
    ]


@pytest.fixture
def cluster_api_sections():
    return [
        "kube_pod_resources_v1",
        "kube_allocatable_pods_v1",
        "kube_node_count_v1",
        "kube_cluster_details_v1",
        "kube_memory_resources_v1",
        "kube_cpu_resources_v1",
        "kube_allocatable_memory_resource_v1",
        "kube_allocatable_cpu_resource_v1",
    ]


@pytest.fixture
def write_sections_mock(mocker):
    return mocker.patch("cmk.special_agents.agent_kube._write_sections")
