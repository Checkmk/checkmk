#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict

import cmk.base.plugins.agent_based.utils.docker as docker

from .agent_based_api.v1 import register, TableRow
from .agent_based_api.v1.type_defs import InventoryResult, StringTable

Section = Dict[str, Dict]


def parse_docker_container_network(string_table: StringTable) -> Section:
    return docker.parse(string_table).data


register.agent_section(
    name="docker_container_network",
    parse_function=parse_docker_container_network,
)


def inventory_docker_container_network_networks(section: Section) -> InventoryResult:
    network_data = section.get("Networks") or {}
    path = ["software", "applications", "docker", "container", "networks"]
    for network_name, network in network_data.items():
        yield TableRow(
            path=path,
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
    port_data = section.get("Ports") or {}
    path = ["software", "applications", "docker", "container", "ports"]
    for container_port_spec, host_ports in port_data.items():
        port, proto = container_port_spec.split("/", 1)

        if host_ports:
            host_addresses = ", ".join(
                ["%s:%s" % (hp["HostIp"], hp["HostPort"]) for hp in host_ports]
            )
        else:
            host_addresses = ""

        yield TableRow(
            path=path,
            key_columns={"port": int(port)},
            inventory_columns={
                "protocol": proto,
                "host_addresses": host_addresses,
            },
        )


def inventory_docker_container_network(section: Section) -> InventoryResult:
    yield from inventory_docker_container_network_networks(section)
    yield from inventory_docker_container_network_ports(section)


register.inventory_plugin(
    name="docker_container_network",
    inventory_function=inventory_docker_container_network,
)
