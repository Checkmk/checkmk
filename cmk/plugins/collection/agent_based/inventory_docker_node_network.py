#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    Attributes,
    InventoryPlugin,
    InventoryResult,
    StringTable,
    TableRow,
)
from cmk.plugins.lib import docker

Section = dict[str, Any]


def parse_docker_node_network(string_table: StringTable) -> Section:
    networks = docker.parse_multiline(string_table).data
    return {n["Id"]: n for n in networks}


agent_section_docker_node_network = AgentSection(
    name="docker_node_network",
    parse_function=parse_docker_node_network,
)


def inventory_docker_node_network(section: Section) -> InventoryResult:
    for network_id, network in section.items():
        network_name = network["Name"]
        network_path = ["software", "applications", "docker", "networks", network_name]
        container_path = network_path + ["containers"]

        for container_id, container in sorted(network["Containers"].items()):
            yield TableRow(
                path=container_path,
                key_columns={
                    "id": docker.get_short_id(container_id),
                },
                status_columns={
                    "name": container["Name"],
                    "ipv4_address": container["IPv4Address"],
                    "ipv6_address": container["IPv6Address"],
                    "mac_address": container["MacAddress"],
                },
            )

        network_inventory_attributes = {
            "name": network_name,
            "network_id": docker.get_short_id(network_id),
            "scope": network["Scope"],
            "labels": docker.format_labels(network.get("Labels", {})),
        }
        try:
            network_inventory_attributes.update(
                host_ifname=network["Options"]["com.docker.network.bridge.name"]
            )
        except KeyError:
            pass

        yield Attributes(
            path=network_path,
            inventory_attributes=network_inventory_attributes,
        )


inventory_plugin_docker_node_network = InventoryPlugin(
    name="docker_node_network",
    inventory_function=inventory_docker_node_network,
)
