#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.special_agents import agent_kube
from cmk.special_agents.utils_kubernetes.schemata import section


def test_cluster_allocatable_memory_resource(node_allocatable_memory, cluster_nodes, cluster):
    expected = section.AllocatableResource(value=node_allocatable_memory * cluster_nodes)
    actual = cluster.allocatable_memory_resource()
    assert actual == expected


def test_cluster_allocatable_cpu_resource(node_allocatable_cpu, cluster_nodes, cluster):
    expected = section.AllocatableResource(value=node_allocatable_cpu * cluster_nodes)
    actual = cluster.allocatable_cpu_resource()
    assert actual == expected


def test_write_cluster_api_sections_registers_sections_to_be_written(
    cluster, cluster_api_sections, write_sections_mock
):
    agent_kube.write_cluster_api_sections(cluster)
    assert list(write_sections_mock.call_args[0][0]) == cluster_api_sections


def test_write_cluster_api_sections_maps_section_names_to_callables(
    cluster, cluster_api_sections, write_sections_mock
):
    agent_kube.write_cluster_api_sections(cluster)
    assert all(
        callable(write_sections_mock.call_args[0][0][section_name])
        for section_name in cluster_api_sections
    )
