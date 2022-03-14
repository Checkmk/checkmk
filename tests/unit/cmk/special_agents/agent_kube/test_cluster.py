#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import io
from contextlib import redirect_stdout
from typing import Callable, Sequence, Tuple

import pytest
from pydantic_factories import ModelFactory

from cmk.base.plugins.agent_based.utils import kube_resources

from cmk.special_agents import agent_kube as agent
from cmk.special_agents.utils_kubernetes.schemata import api, section

from .conftest import (
    api_to_agent_cluster,
    APINodeFactory,
    APIPodFactory,
    NodeMetaDataFactory,
    NodeResourcesFactory,
    ONE_GiB,
    PodSpecFactory,
    PodStatusFactory,
)


class PerformanceMetricFactory(ModelFactory):
    __model__ = agent.PerformanceMetric


class RateMetricFactory(ModelFactory):
    __model__ = agent.RateMetric


class PerformanceContainerFactory(ModelFactory):
    __model__ = agent.PerformanceContainer


def test_cluster_namespaces(cluster_details: api.ClusterDetails, pod_metadata: api.PodMetaData):
    cluster = agent.Cluster(cluster_details=cluster_details, excluded_node_roles=[])
    api_pod = APIPodFactory.build(metadata=pod_metadata)
    cluster.add_pod(
        agent.Pod(
            api_pod.uid,
            api_pod.metadata,
            api_pod.status,
            api_pod.spec,
            api_pod.containers,
            api_pod.init_containers,
        )
    )
    assert cluster.namespaces() == {pod_metadata.namespace}


@pytest.mark.parametrize("cluster_pods", [0, 10, 20])
def test_cluster_resources(
    cluster_details: api.ClusterDetails,
    cluster_pods: int,
    new_pod: Callable[[], agent.Pod],
    pod_containers_count: int,
):
    cluster = agent.Cluster(cluster_details=cluster_details, excluded_node_roles=[])
    for _ in range(cluster_pods):
        cluster.add_pod(new_pod())
    assert cluster.memory_resources().count_total == cluster_pods * pod_containers_count
    assert cluster.cpu_resources().count_total == cluster_pods * pod_containers_count
    assert sum(len(pods) for _phase, pods in cluster.pod_resources()) == cluster_pods


def test_cluster_allocatable_memory_resource(
    node_allocatable_memory: float, cluster_nodes: int, cluster: agent.Cluster
):
    expected = section.AllocatableResource(
        context="cluster", value=node_allocatable_memory * cluster_nodes
    )
    actual = cluster.allocatable_memory_resource()
    assert actual == expected


def test_cluster_allocatable_cpu_resource(
    node_allocatable_cpu: float, cluster_nodes: int, cluster: agent.Cluster
):
    expected = section.AllocatableResource(
        context="cluster", value=node_allocatable_cpu * cluster_nodes
    )
    actual = cluster.allocatable_cpu_resource()
    assert actual == expected


def test_write_cluster_api_sections_registers_sections_to_be_written(
    cluster: agent.Cluster, cluster_api_sections: Sequence[str], write_sections_mock
):
    agent.write_cluster_api_sections("cluster", cluster)
    assert list(write_sections_mock.call_args[0][0]) == cluster_api_sections


def test_write_cluster_api_sections_maps_section_names_to_callables(
    cluster: agent.Cluster, cluster_api_sections: Sequence[str], write_sections_mock
):
    agent.write_cluster_api_sections("cluster", cluster)
    assert all(
        callable(write_sections_mock.call_args[0][0][section_name])
        for section_name in cluster_api_sections
    )


@pytest.mark.parametrize("cluster_nodes", [0, 10, 20])
def test_node_count_returns_number_of_nodes_ready_not_ready(
    cluster_nodes: int, cluster: agent.Cluster
):
    node_count = cluster.node_count()
    assert node_count.worker.ready + node_count.worker.not_ready == cluster_nodes


@pytest.mark.parametrize("node_is_control_plane", [True])
def test_node_control_plane_count(cluster_details: api.ClusterDetails, node: agent.Node):
    cluster = agent.Cluster(cluster_details=cluster_details, excluded_node_roles=[])
    cluster.add_node(node)
    node_count = cluster.node_count()
    assert node_count.worker.total == 0
    assert node_count.control_plane.total == 1
    assert node_count.control_plane.ready == 1


@pytest.mark.parametrize("node_is_control_plane", [True])
@pytest.mark.parametrize("node_condition_status", [api.ConditionStatus.FALSE])
def test_node_control_plane_not_ready_count(cluster_details: api.ClusterDetails, node: agent.Node):
    cluster = agent.Cluster(cluster_details=cluster_details, excluded_node_roles=[])
    cluster.add_node(node)
    node_count = cluster.node_count()
    assert node_count.control_plane.not_ready == 1


@pytest.mark.parametrize("cluster_daemon_sets", [0, 10, 20])
def test_daemon_sets_returns_daemon_sets_of_cluster(
    cluster_daemon_sets: int, cluster: agent.Cluster
):
    daemon_sets = cluster.daemon_sets()
    assert len(daemon_sets) == cluster_daemon_sets


@pytest.mark.parametrize("cluster_statefulsets", [0, 10, 20])
def test_statefulsets_returns_statefulsets_of_cluster(cluster_statefulsets, cluster):
    statefulsets = cluster.statefulsets()
    assert len(statefulsets) == cluster_statefulsets


# Tests for exclusion via node role


@pytest.mark.parametrize("excluded_node_roles", [["control-plane"], [], ["master"]])
@pytest.mark.parametrize(
    "api_node_roles_per_node, cluster_nodes, expected_control_nodes",
    [
        (
            [["control-piano"], ["gold"], ["silver"]],
            3,
            0,
        ),
        (
            [["control-plane"], ["gold"], ["control-plane"]],
            3,
            2,
        ),
        (
            [["control-plane, blue"], ["vegis", "control-plane, fish"], ["control-plane"]],
            3,
            3,
        ),
    ],
)
def test_cluster_allocatable_memory_resource_exclude_roles(
    api_node_roles_per_node: Sequence[Sequence[str]],
    cluster_nodes: int,
    excluded_node_roles: Sequence[str],
    expected_control_nodes: int,
):
    counted_nodes = (
        cluster_nodes - expected_control_nodes
        if "control-plane" in excluded_node_roles
        else cluster_nodes
    )
    expected = section.AllocatableResource(context="cluster", value=7.0 * ONE_GiB * counted_nodes)
    cluster = api_to_agent_cluster(
        excluded_node_roles=excluded_node_roles,
        nodes=[
            APINodeFactory.build(
                resources={"allocatable": NodeResourcesFactory.build(memory=7.0 * ONE_GiB)},
                roles=roles,
            )
            for roles in api_node_roles_per_node
        ],
    )
    actual = cluster.allocatable_memory_resource()
    assert actual == expected


@pytest.mark.parametrize("excluded_node_roles", [["control-plane"], [], ["master"]])
@pytest.mark.parametrize(
    "api_node_roles_per_node, cluster_nodes, expected_control_nodes",
    [
        (
            [["control-piano"], ["gold"], ["silver"]],
            3,
            0,
        ),
        (
            [["control-plane"], ["gold"], ["control-plane"]],
            3,
            2,
        ),
        (
            [["control-plane, blue"], ["vegis", "control-plane, fish"], ["control-plane"]],
            3,
            3,
        ),
    ],
)
def test_cluster_allocatable_cpu_resource_cluster(
    api_node_roles_per_node: Sequence[Sequence[str]],
    cluster_nodes: int,
    excluded_node_roles: Sequence[str],
    expected_control_nodes: int,
):
    counted_nodes = (
        cluster_nodes - expected_control_nodes
        if "control-plane" in excluded_node_roles
        else cluster_nodes
    )
    expected = section.AllocatableResource(context="cluster", value=6.0 * counted_nodes)
    cluster = api_to_agent_cluster(
        excluded_node_roles=excluded_node_roles,
        nodes=[
            APINodeFactory.build(
                resources={"allocatable": NodeResourcesFactory.build(cpu=6.0)},
                roles=roles,
            )
            for roles in api_node_roles_per_node
        ],
    )
    actual = cluster.allocatable_cpu_resource()
    assert actual == expected


@pytest.mark.parametrize(
    "excluded_node_role, node_podcount_roles",
    [
        (
            "control-plane",
            [
                ("a", 3, ["control-plane"]),
                ("b", 2, ["worker"]),
            ],
        ),
        (
            "master",
            [
                ("a", 3, ["master"]),
                ("b", 2, ["master"]),
            ],
        ),
    ],
)
def test_cluster_usage_resources(
    excluded_node_role: str,
    node_podcount_roles: Sequence[Tuple[str, int, Sequence[str]]],
):
    total = sum(count for _, count, roles in node_podcount_roles if excluded_node_role not in roles)
    pods = [
        pod
        for node, count, _ in node_podcount_roles
        for pod in APIPodFactory.batch(count, spec=PodSpecFactory.build(node=node))
    ]
    nodes = [
        APINodeFactory.build(metadata=NodeMetaDataFactory.build(name=node), roles=roles)
        for node, _, roles in node_podcount_roles
    ]
    cluster = api_to_agent_cluster(
        excluded_node_roles=[excluded_node_role],
        pods=pods,
        nodes=nodes,
    )

    assert cluster.memory_resources().count_total == len(APIPodFactory.build().containers) * total
    assert cluster.cpu_resources().count_total == len(APIPodFactory.build().containers) * total
    assert sum(len(pods) for _, pods in cluster.pod_resources()) == total


@pytest.mark.parametrize(
    "excluded_node_role, node_podcount_roles",
    [
        (
            "control-plane",
            [
                ("a", 3, ["control-plane"]),
                ("b", 2, ["worker"]),
            ],
        ),
        (
            "master",
            [
                ("a", 3, ["master"]),
                ("b", 2, ["master"]),
            ],
        ),
    ],
)
def test_cluster_allocatable_pods(
    excluded_node_role: str,
    node_podcount_roles: Sequence[Tuple[str, int, Sequence[str]]],
):
    allocatable = 110
    capacity = 111  # can not be different in pratice, but better for testing
    total = sum(1 for *_, roles in node_podcount_roles if excluded_node_role not in roles)
    pods = [
        pod
        for node, count, _ in node_podcount_roles
        for pod in APIPodFactory.batch(count, spec=PodSpecFactory.build(node=node))
    ]
    nodes = [
        APINodeFactory.build(
            metadata=NodeMetaDataFactory.build(name=node),
            resources={
                "allocatable": NodeResourcesFactory.build(pods=allocatable),
                "capacity": NodeResourcesFactory.build(pods=capacity),
            },
            roles=roles,
        )
        for node, _, roles in node_podcount_roles
    ]
    cluster = api_to_agent_cluster(
        excluded_node_roles=[excluded_node_role],
        pods=pods,
        nodes=nodes,
    )

    assert cluster.allocatable_pods().capacity == total * capacity
    assert cluster.allocatable_pods().allocatable == total * allocatable


@pytest.mark.parametrize("phase_all_pods", list(api.Phase))
@pytest.mark.parametrize(
    "excluded_node_role, node_podcount_roles",
    [
        (
            "control-plane",
            [
                ("a", 3, ["control-plane"]),
                ("b", 2, ["worker"]),
            ],
        ),
        (
            "master",
            [
                ("a", 3, ["master"]),
                ("b", 2, ["master"]),
            ],
        ),
    ],
)
def test_write_kube_object_performance_section_cluster(
    phase_all_pods: api.Phase,
    excluded_node_role: str,
    node_podcount_roles: Sequence[Tuple[str, int, Sequence[str]]],
):
    # Initialize API data
    pods = [
        pod
        for node, count, _ in node_podcount_roles
        for pod in APIPodFactory.batch(
            count,
            spec=PodSpecFactory.build(node=node),
            status=PodStatusFactory.build(phase=phase_all_pods),
        )
    ]
    nodes = [
        APINodeFactory.build(
            metadata=NodeMetaDataFactory.build(name=node),
            roles=roles,
        )
        for node, _, roles in node_podcount_roles
    ]
    cluster = api_to_agent_cluster(
        excluded_node_roles=[excluded_node_role],
        pods=pods,
        nodes=nodes,
    )

    # Initialize cluster collector data
    container_count = 3  # this count may differ from the one used to generate API data
    performance_pods = {
        agent.pod_lookup_from_api_pod(pod): agent.PerformancePod(
            lookup_name=agent.pod_lookup_from_api_pod(pod),
            containers=PerformanceContainerFactory.batch(
                container_count,
                metrics={
                    "memory_working_set_bytes": PerformanceMetricFactory.build(value=1.0 * ONE_GiB),
                },
                rate_metrics={"cpu_usage_seconds_total": RateMetricFactory.build(rate=1.0)},
            ),
        )
        for pod in pods
    }

    # Write Cluster performance sections to output by capturing stdout
    with io.StringIO() as buf, redirect_stdout(buf):
        agent.write_kube_object_performance_section_cluster(cluster, performance_pods)
        output = buf.getvalue().splitlines()

    # Check correctness
    total = (
        sum(count for _, count, roles in node_podcount_roles if excluded_node_role not in roles)
        if phase_all_pods == api.Phase.RUNNING
        else 0
    )
    if total == 0:
        # If there are no running pods on non-filtered nodes, no sections should be produced
        assert "<<<kube_performance_cpu_v1:sep(0)>>>" not in output
        assert "<<<kube_performance_memory_v1:sep(0)>>>" not in output
    else:
        for current_row, next_row in zip(output[:-1], output[1:]):
            if current_row == "<<<kube_performance_cpu_v1:sep(0)>>>":
                cpu_section = kube_resources.parse_performance_usage([[next_row]])
            elif current_row == "<<<kube_performance_memory_v1:sep(0)>>>":
                memory_section = kube_resources.parse_performance_usage([[next_row]])
        assert cpu_section.resource.usage == total * container_count * 1.0
        assert memory_section.resource.usage == total * container_count * 1.0 * ONE_GiB
