#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Any

from cmk.agent_based.v2 import AgentSection, InventoryPlugin, InventoryResult, StringTable, TableRow
from cmk.plugins.lib import docker

SectionStandard = dict[str, Any]

Section = SectionStandard | docker.MultipleNodesMarker


def parse_docker_container_network(string_table: StringTable) -> Section:
    return (
        docker.MultipleNodesMarker()
        if len(docker.cleanup_oci_error_message(string_table)) > 2
        else docker.parse(string_table, strict=False).data
    )


agent_section_docker_container_network = AgentSection(
    name="docker_container_network",
    parse_function=parse_docker_container_network,
)


def inventory_docker_container_network_networks(section: Section) -> InventoryResult:
    if isinstance(section, docker.MultipleNodesMarker):
        return

    network_data = section.get("Networks") or {}
    for network_name, network in network_data.items():
        yield TableRow(
            path=["software", "applications", "docker", "container", "networks"],
            key_columns={
                "name": network_name,
                "network_id": network["NetworkID"],
            },
            inventory_columns={
                "ip_address": network["IPAddress"],
                "ip_prefixlen": network["IPPrefixLen"],
                "gateway": network["Gateway"],
                "mac_address": network["MacAddress"],
            },
        )


def inventory_docker_container_network_ports(section: Section) -> InventoryResult:
    if isinstance(section, docker.MultipleNodesMarker):
        return

    port_data = section.get("Ports") or {}
    for container_port_spec, host_ports in port_data.items():
        port, proto = container_port_spec.split("/", 1)

        if host_ports:
            host_addresses = ", ".join(
                ["{}:{}".format(hp["HostIp"], hp["HostPort"]) for hp in host_ports]
            )
        else:
            host_addresses = ""

        yield TableRow(
            path=["software", "applications", "docker", "container", "ports"],
            key_columns={"port": int(port)},
            inventory_columns={
                "protocol": proto,
                "host_addresses": host_addresses,
            },
        )


def inventory_docker_container_network(section: Section) -> InventoryResult:
    yield from inventory_docker_container_network_networks(section)
    yield from inventory_docker_container_network_ports(section)


inventory_plugin_docker_container_network = InventoryPlugin(
    name="docker_container_network",
    inventory_function=inventory_docker_container_network,
)
