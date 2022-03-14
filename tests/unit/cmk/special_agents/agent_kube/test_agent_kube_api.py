#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=comparison-with-callable,redefined-outer-name

from typing import Optional

import pytest
from pydantic_factories import ModelFactory

from cmk.special_agents.agent_kube import aggregate_resources, Cluster
from cmk.special_agents.utils_kubernetes.schemata import api


@pytest.fixture
def node_name():
    return "node"


@pytest.fixture
def api_node(node_name):
    class APINode(ModelFactory):
        __model__ = api.Node

    node = APINode.build()
    node.metadata.name = node_name
    return node


@pytest.fixture
def api_pod(node_name):
    class APIPod(ModelFactory):
        __model__ = api.Pod

    pod = APIPod.build()
    pod.spec.node = node_name
    return pod


def test_pod_node_allocation_within_cluster(api_node, api_pod):
    """Test pod is correctly allocated to node within cluster"""
    cluster = Cluster.from_api_resources(
        pods=[api_pod],
        nodes=[api_node],
        statefulsets=[],
    )
    assert len(cluster.nodes()) == 1
    assert len(cluster.nodes()[0].pods()) == 1


def test_pod_deployment_allocation_within_cluster(api_node, api_pod):
    """Test pod is correctly allocated to deployment within cluster"""

    class APIDeployment(ModelFactory):
        __model__ = api.Deployment

    deployment = APIDeployment.build()
    deployment.pods = [api_pod.uid]
    cluster = Cluster.from_api_resources(
        pods=[api_pod],
        nodes=[api_node],
        statefulsets=[],
        deployments=[deployment],
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
