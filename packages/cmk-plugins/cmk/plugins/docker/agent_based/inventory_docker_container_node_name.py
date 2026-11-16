#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v2 import (
    AgentSection,
    Attributes,
    InventoryPlugin,
    InventoryResult,
    StringTable,
)
from cmk.plugins.docker import lib as docker

Section = Mapping[str, object] | docker.MultipleNodesMarker


def parse_docker_container_node_name(string_table: StringTable) -> Section:
    return (
        docker.MultipleNodesMarker()
        if len(docker.cleanup_oci_error_message(string_table)) > 2
        else docker.parse(string_table, strict=False).data
    )


agent_section_docker_container_node_name = AgentSection(
    name="docker_container_node_name",
    parse_function=parse_docker_container_node_name,
)


def inventorize_docker_container_node_name(section: Section) -> InventoryResult:
    if isinstance(section, docker.MultipleNodesMarker):
        return

    if (node := section.get("NodeName")) is not None:
        yield Attributes(
            path=["software", "applications", "docker", "container"],
            inventory_attributes={"node_name": str(node)},
        )


inventory_plugin_docker_container_node_name = InventoryPlugin(
    name="docker_container_node_name",
    inventory_function=inventorize_docker_container_node_name,
)
