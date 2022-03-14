#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from pydantic_factories import ModelFactory

from cmk.special_agents import agent_kube
from cmk.special_agents.utils_kubernetes.schemata.section import (
    CheckmkKubeAgentMetadata,
    CollectorType,
    Components,
    NodeCollectorMetadata,
    NodeComponent,
    NodeMetadata,
    Version,
)


class NodeCollectorMetadataFactory(ModelFactory):
    __model__ = NodeCollectorMetadata


class NodeComponentFactory(ModelFactory):
    __model__ = NodeComponent


class NodeMetadataFactory(ModelFactory):
    __model__ = NodeMetadata


def components(collector_type: CollectorType) -> Components:
    if collector_type == CollectorType.MACHINE_SECTIONS:
        return Components(cadvisor_version=None, checkmk_agent_version="1.0.0")
    if collector_type == CollectorType.CONTAINER_METRICS:
        return Components(cadvisor_version="1.0.0", checkmk_agent_version=None)
    raise ValueError("Unknown collector type: %s" % collector_type)


def node_collector_metadata(collector_type: CollectorType, node_name: str) -> NodeCollectorMetadata:
    return NodeCollectorMetadataFactory.build(
        collector_type=collector_type, node=node_name, components=components(collector_type)
    )


def node_component(project_version: Version) -> NodeComponent:
    return NodeComponentFactory.build(
        checkmk_kube_agent=CheckmkKubeAgentMetadata(project_version=project_version)
    )


def test_group_metadata_by_node():
    node_name = "node"
    node_collector_machine = node_collector_metadata(CollectorType.MACHINE_SECTIONS, node_name)
    node_collector_container = node_collector_metadata(CollectorType.CONTAINER_METRICS, node_name)
    grouped_metadata = agent_kube._group_metadata_by_node(
        [node_collector_machine, node_collector_container]
    )
    assert len(grouped_metadata) == 1
    assert len(grouped_metadata[0].components) == 2


def test_identify_unsupported_node_collector_components_with_invalid_version():
    version = 2
    component = node_component(Version(str(version)))
    node_metadata = NodeMetadataFactory.build(components={component.name: component})
    invalid_nodes = agent_kube._identify_unsupported_node_collector_components(
        [node_metadata], supported_max_major_version=version - 1
    )
    assert len(invalid_nodes) == 1
