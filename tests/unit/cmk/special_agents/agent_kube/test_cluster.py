#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Sequence

import pytest

from cmk.special_agents import agent_kube
from cmk.special_agents.utils_kubernetes.schemata import section


def test_cluster_allocatable_memory_resource(
    node_allocatable_memory: float, cluster_nodes: int, cluster: agent_kube.Cluster
):
    expected = section.AllocatableResource(
        context="cluster", value=node_allocatable_memory * cluster_nodes
    )
    actual = cluster.allocatable_memory_resource()
    assert actual == expected


def test_cluster_allocatable_cpu_resource(
    node_allocatable_cpu: float, cluster_nodes: int, cluster: agent_kube.Cluster
):
    expected = section.AllocatableResource(
        context="cluster", value=node_allocatable_cpu * cluster_nodes
    )
    actual = cluster.allocatable_cpu_resource()
    assert actual == expected


def test_write_cluster_api_sections_registers_sections_to_be_written(
    cluster: agent_kube.Cluster, cluster_api_sections: Sequence[str], write_sections_mock
):
    agent_kube.write_cluster_api_sections("cluster", cluster)
    assert list(write_sections_mock.call_args[0][0]) == cluster_api_sections


def test_write_cluster_api_sections_maps_section_names_to_callables(
    cluster: agent_kube.Cluster, cluster_api_sections: Sequence[str], write_sections_mock
):
    agent_kube.write_cluster_api_sections("cluster", cluster)
    assert all(
        callable(write_sections_mock.call_args[0][0][section_name])
        for section_name in cluster_api_sections
    )


@pytest.mark.parametrize("cluster_nodes", [0, 10, 20])
def test_node_count_returns_number_of_nodes_ready_not_ready(
    cluster_nodes: int, cluster: agent_kube.Cluster
):
    node_count = cluster.node_count()
    assert node_count.worker.ready + node_count.worker.not_ready == cluster_nodes


@pytest.mark.parametrize("cluster_daemon_sets", [0, 10, 20])
def test_daemon_sets_returns_daemon_sets_of_cluster(
    cluster_daemon_sets: int, cluster: agent_kube.Cluster
):
    daemon_sets = cluster.daemon_sets()
    assert len(daemon_sets) == cluster_daemon_sets


@pytest.mark.parametrize("cluster_statefulsets", [0, 10, 20])
def test_statefulsets_returns_statefulsets_of_cluster(cluster_statefulsets, cluster):
    statefulsets = cluster.statefulsets()
    assert len(statefulsets) == cluster_statefulsets
