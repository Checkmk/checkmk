#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=comparison-with-callable,redefined-outer-name

from typing import Optional, Sequence

import pytest
from pydantic_factories import ModelFactory

from tests.unit.cmk.special_agents.agent_kube.factory import (
    api_to_agent_pod,
    APIPodFactory,
    pod_phase_generator,
    PodMetaDataFactory,
    PodSpecFactory,
    PodStatusFactory,
)

from cmk.special_agents import agent_kube as agent
from cmk.special_agents.agent_kube import aggregate_resources, Cluster
from cmk.special_agents.utils_kubernetes.schemata import api, section


class ContainerResourcesFactory(ModelFactory):
    __model__ = api.ContainerResources


class ClusterDetailsFactory(ModelFactory):
    __model__ = api.ClusterDetails


class ContainerSpecFactory(ModelFactory):
    __model__ = api.ContainerSpec


class APIDeployment(ModelFactory):
    __model__ = api.Deployment


class APINode(ModelFactory):
    __model__ = api.Node


class ResourcesRequirementsFactory(ModelFactory):
    __model__ = api.ResourcesRequirements


@pytest.fixture
def node_name():
    return "node"


@pytest.fixture
def api_node(node_name):
    node = APINode.build()
    node.metadata.name = node_name
    return node


@pytest.fixture
def api_pod(node_name):
    pod = APIPodFactory.build()
    pod.spec.node = node_name
    return pod


def test_pod_node_allocation_within_cluster(
    api_node: api.Node, api_pod: api.Pod, cluster_details: api.ClusterDetails
):
    """Test pod is correctly allocated to node within cluster"""
    cluster = Cluster.from_api_resources(
        excluded_node_roles=[],
        pods=[api_pod],
        nodes=[api_node],
        statefulsets=[],
        daemon_sets=[],
        cron_jobs=[],
        deployments=[],
        cluster_details=cluster_details,
    )
    assert len(cluster.nodes()) == 1
    assert len(cluster.nodes()[0].pods()) == 1


def test_pod_deployment_allocation_within_cluster(api_node, api_pod) -> None:
    """Test pod is correctly allocated to deployment within cluster"""

    class APIDeployment(ModelFactory):
        __model__ = api.Deployment

    deployment = APIDeployment.build()
    deployment.pods = [api_pod.uid]
    cluster = Cluster.from_api_resources(
        excluded_node_roles=[],
        pods=[api_pod],
        nodes=[api_node],
        statefulsets=[],
        daemon_sets=[],
        cron_jobs=[],
        deployments=[deployment],
        cluster_details=ClusterDetailsFactory.build(),
    )
    assert len(cluster.deployments()) == 1


ONE_KiB = 1024
ONE_MiB = 1024 * ONE_KiB


def container_spec(
    request_cpu: Optional[float] = 1.0,
    limit_cpu: Optional[float] = 2.0,
    request_memory: Optional[float] = 1.0 * ONE_MiB,
    limit_memory: Optional[float] = 2.0 * ONE_MiB,
) -> api.ContainerSpec:
    class ContainerSpecFactory(ModelFactory):
        __model__ = api.ContainerSpec

        resources = api.ContainerResources(
            limits=api.ResourcesRequirements(memory=limit_memory, cpu=limit_cpu),
            requests=api.ResourcesRequirements(memory=request_memory, cpu=request_cpu),
        )

    return ContainerSpecFactory.build()


def test_aggregate_resources_summed_request_cpu() -> None:
    container_specs = [container_spec(request_cpu=request) for request in [None, 1.0, 1.0]]
    result = aggregate_resources("cpu", container_specs)
    assert result.request == 2.0
    assert result.count_unspecified_requests == 1


def test_aggregate_resources_summed_request_memory() -> None:
    container_specs = [
        container_spec(request_memory=request) for request in [None, 1.0 * ONE_MiB, 1.0 * ONE_MiB]
    ]
    result = aggregate_resources("memory", container_specs)
    assert result.request == 2.0 * ONE_MiB
    assert result.count_unspecified_requests == 1


def test_aggregate_resources_summed_limit_cpu() -> None:
    container_specs = [container_spec(limit_cpu=limit) for limit in [None, 1.0, 1.0]]
    result = aggregate_resources("cpu", container_specs)
    assert result.limit == 2.0
    assert result.count_unspecified_limits == 1


def test_aggregate_resources_summed_limit_memory() -> None:
    container_specs = [
        container_spec(limit_memory=limit) for limit in [None, 1.0 * ONE_MiB, 1.0 * ONE_MiB]
    ]
    result = aggregate_resources("memory", container_specs)
    assert result.limit == 2.0 * ONE_MiB


def test_aggregate_resources_with_only_zeroed_limit_cpu() -> None:
    container_specs = [container_spec(limit_cpu=limit) for limit in [0.0, 0.0]]
    result = aggregate_resources("cpu", container_specs)
    assert result.count_zeroed_limits == 2


def test_aggregate_resources_with_only_zeroed_limit_memory() -> None:
    container_specs = [container_spec(limit_memory=limit) for limit in [0.0, 0.0]]
    result = aggregate_resources("memory", container_specs)
    assert result.count_zeroed_limits == 2


@pytest.mark.parametrize("pods_count", [0, 5])
def test_pod_resources_from_api_pods(pods_count: int) -> None:
    pods = [
        APIPodFactory.build(
            metadata=PodMetaDataFactory.build(name=str(i)),
            status=PodStatusFactory.build(
                phase=api.Phase.RUNNING,
            ),
        )
        for i in range(pods_count)
    ]

    pod_resources = agent._pod_resources_from_api_pods(pods)

    assert pod_resources == section.PodResources(
        running=[str(i) for i in range(pods_count)],
    )


def test_pod_name() -> None:
    name = "name"
    namespace = "namespace"
    pod = APIPodFactory.build(metadata=PodMetaDataFactory.build(name=name, namespace=namespace))

    pod_name = agent.pod_name(pod)
    pod_namespaced_name = agent.pod_name(pod, prepend_namespace=True)

    assert pod_name == name
    assert pod_namespaced_name == f"{namespace}_{name}"


def test_filter_pods_by_namespace() -> None:
    pod_one = APIPodFactory.build(
        metadata=PodMetaDataFactory.build(name="pod_one", namespace="one")
    )
    pod_two = APIPodFactory.build(
        metadata=PodMetaDataFactory.build(name="pod_two", namespace="two")
    )

    filtered_pods = agent.filter_pods_by_namespace([pod_one, pod_two], api.NamespaceName("one"))

    assert [pod.metadata.name for pod in filtered_pods] == ["pod_one"]


@pytest.mark.parametrize(
    "phase",
    [
        api.Phase.PENDING,
        api.Phase.RUNNING,
        api.Phase.FAILED,
        api.Phase.SUCCEEDED,
        api.Phase.UNKNOWN,
    ],
)
def test_filter_pods_by_phase(phase: api.Phase) -> None:
    pods_count = len(api.Phase)
    phases = pod_phase_generator()
    pods = [
        APIPodFactory.build(status=PodStatusFactory.build(phase=next(phases)))
        for _ in range(pods_count)
    ]

    pods_in_phase = agent.filter_pods_by_phase(pods, phase)

    assert [pod.status.phase for pod in pods_in_phase] == [phase]


@pytest.mark.parametrize("pods_count", [0, 5])
def test_collect_workload_resources_from_api_pods(pods_count: int) -> None:
    requirements = ResourcesRequirementsFactory.build(memory=ONE_MiB, cpu=0.5)
    pods = [
        APIPodFactory.build(
            spec=PodSpecFactory.build(
                containers=[
                    ContainerSpecFactory.build(
                        resources=ContainerResourcesFactory.build(
                            limits=requirements, requests=requirements
                        )
                    )
                ]
            )
        )
        for _ in range(pods_count)
    ]

    memory_resources = agent._collect_memory_resources_from_api_pods(pods)
    cpu_resources = agent._collect_cpu_resources_from_api_pods(pods)

    assert memory_resources == section.Resources(
        request=pods_count * ONE_MiB,
        limit=pods_count * ONE_MiB,
        count_unspecified_limits=0,
        count_unspecified_requests=0,
        count_zeroed_limits=0,
        count_total=pods_count,
    )

    assert cpu_resources == section.Resources(
        request=pods_count * 0.5,
        limit=pods_count * 0.5,
        count_unspecified_limits=0,
        count_unspecified_requests=0,
        count_zeroed_limits=0,
        count_total=pods_count,
    )


@pytest.mark.parametrize("pods_count", [5, 10, 15])
def test_collect_workload_resources_from_agent_pods(pods_count: int) -> None:
    requests = ResourcesRequirementsFactory.build(memory=ONE_MiB, cpu=0.5)
    limits = ResourcesRequirementsFactory.build(memory=2 * ONE_MiB, cpu=1.0)
    pods = [
        api_to_agent_pod(
            APIPodFactory.build(
                spec=PodSpecFactory.build(
                    containers=[
                        ContainerSpecFactory.build(
                            resources=ContainerResourcesFactory.build(
                                limits=limits, requests=requests
                            )
                        )
                    ]
                )
            )
        )
        for _ in range(pods_count)
    ]

    memory_resources = agent._collect_memory_resources(pods)
    cpu_resources = agent._collect_cpu_resources(pods)

    assert memory_resources == section.Resources(
        request=pods_count * ONE_MiB,
        limit=pods_count * ONE_MiB * 2,
        count_unspecified_limits=0,
        count_unspecified_requests=0,
        count_zeroed_limits=0,
        count_total=pods_count,
    )

    assert cpu_resources == section.Resources(
        request=pods_count * 0.5,
        limit=pods_count * 1.0,
        count_unspecified_limits=0,
        count_unspecified_requests=0,
        count_zeroed_limits=0,
        count_total=pods_count,
    )


def test_collect_workload_resources_from_agent_pods_no_pods_in_cluster() -> None:
    pods: Sequence[agent.Pod] = []
    memory_resources = agent._collect_memory_resources(pods)
    cpu_resources = agent._collect_cpu_resources(pods)
    empty_section = section.Resources(
        request=0.0,
        limit=0.0,
        count_unspecified_limits=0,
        count_unspecified_requests=0,
        count_zeroed_limits=0,
        count_total=0,
    )

    assert memory_resources == empty_section
    assert cpu_resources == empty_section
