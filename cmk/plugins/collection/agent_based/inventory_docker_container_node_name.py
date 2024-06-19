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
from cmk.plugins.lib import docker

Section = Mapping[str, object]


def parse_docker_container_node_name(string_table: StringTable) -> Section:
    return docker.parse(string_table).data


agent_section_inventory_docker_container_node_name = AgentSection(
    name="inventory_docker_container_node_name",
    parse_function=parse_docker_container_node_name,
)


def inventory_docker_container_node_name(section: Section) -> InventoryResult:
    if (node := section.get("NodeName")) is not None:
        yield Attributes(
            path=["software", "applications", "docker", "container"],
            inventory_attributes={"node_name": str(node)},
        )


inventory_plugin_inventory_docker_container_node_name = InventoryPlugin(
    name="inventory_docker_container_node_name",
    inventory_function=inventory_docker_container_node_name,
)
