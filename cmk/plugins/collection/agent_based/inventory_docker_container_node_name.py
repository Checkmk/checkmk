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

Section = Mapping[str, object]


def parse_docker_container_node_name(string_table: StringTable) -> Section:
    return docker.parse(string_table).data


agent_section_inventorize_docker_container_node_name = AgentSection(
    name="inventorize_docker_container_node_name",
    parse_function=parse_docker_container_node_name,
)


def inventorize_docker_container_node_name(section: Section) -> InventoryResult:
    if (node := section.get("NodeName")) is not None:
        yield Attributes(
            path=["software", "applications", "docker", "container"],
            inventory_attributes={"node_name": str(node)},
        )


inventory_plugin_inventorize_docker_container_node_name = InventoryPlugin(
    name="inventorize_docker_container_node_name",
    inventory_function=inventorize_docker_container_node_name,
)
