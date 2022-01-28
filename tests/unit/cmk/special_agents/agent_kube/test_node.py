#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from unittest.mock import Mock

from cmk.special_agents import agent_kube
from cmk.special_agents.utils_kubernetes.schemata import section


def test_node_allocatable_memory_resource(node_allocatable_memory, node):
    expected = section.AllocatableResource(value=node_allocatable_memory)
    actual = node.allocatable_memory_resource()
    assert actual == expected


def test_node_allocatable_cpu_resource(node_allocatable_cpu, node):
    expected = section.AllocatableResource(value=node_allocatable_cpu)
    actual = node.allocatable_cpu_resource()
    assert actual == expected


def test_write_nodes_api_sections_registers_sections_to_be_written(
    node, nodes_api_sections, write_sections_mock
):
    agent_kube.write_nodes_api_sections([node], Mock())
    assert list(write_sections_mock.call_args[0][0]) == nodes_api_sections


def test_write_nodes_api_sections_maps_section_names_to_callables(
    node, nodes_api_sections, write_sections_mock
):
    agent_kube.write_nodes_api_sections([node], Mock())
    assert all(
        callable(write_sections_mock.call_args[0][0][section_name])
        for section_name in nodes_api_sections
    )


def test_write_nodes_api_sections_calls_write_sections_for_each_node(
    new_node, cluster_nodes, write_sections_mock
):
    agent_kube.write_nodes_api_sections([new_node() for _ in range(cluster_nodes)], Mock())
    assert write_sections_mock.call_count == cluster_nodes
