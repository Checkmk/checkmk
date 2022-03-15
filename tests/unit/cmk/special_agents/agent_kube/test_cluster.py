#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Callable, Sequence

import pytest
from pydantic_factories import ModelFactory

from cmk.special_agents import agent_kube as agent
from cmk.special_agents.utils_kubernetes.schemata import api, section


class APIPodFactory(ModelFactory):
    __model__ = api.Pod


def test_cluster_namespaces(cluster_details: api.ClusterDetails, pod_metadata: api.PodMetaData):
    cluster = agent.Cluster(cluster_details=cluster_details)
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
    cluster = agent.Cluster(cluster_details=cluster_details)
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
    cluster = agent.Cluster(cluster_details=cluster_details)
    cluster.add_node(node)
    node_count = cluster.node_count()
    assert node_count.worker.total == 0
    assert node_count.control_plane.total == 1
    assert node_count.control_plane.ready == 1


@pytest.mark.parametrize("node_is_control_plane", [True])
@pytest.mark.parametrize("node_condition_status", [api.ConditionStatus.FALSE])
def test_node_control_plane_not_ready_count(cluster_details: api.ClusterDetails, node: agent.Node):
    cluster = agent.Cluster(cluster_details=cluster_details)
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
