#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.inventory_ui.v1_unstable import (
    DecimalNotation,
    Node,
    NumberField,
    SINotation,
    StrictPrecision,
    Table,
    TextField,
    Title,
    Unit,
    View,
)

UNIT_BYTES = Unit(SINotation("B"))
UNIT_COUNT = Unit(DecimalNotation(""), StrictPrecision(0))

node_software_applications_docker = Node(
    name="software_applications_docker",
    path=["software", "applications", "docker"],
    title=Title("Docker"),
    attributes={
        "version": TextField(Title("Version")),
        "registry": TextField(Title("Registry")),
        "swarm_state": TextField(Title("Swarm state")),
        "swarm_node_id": TextField(Title("Swarm node ID")),
        "num_containers_total": NumberField(Title("#Containers"), render=UNIT_COUNT),
        "num_containers_running": NumberField(Title("#Containers running"), render=UNIT_COUNT),
        "num_containers_stopped": NumberField(Title("#Containers stopped"), render=UNIT_COUNT),
        "num_containers_paused": NumberField(Title("#Containers paused"), render=UNIT_COUNT),
        "num_images": NumberField(Title("#Images"), render=UNIT_COUNT),
    },
)

node_software_applications_docker_container = Node(
    name="software_applications_docker_container",
    path=["software", "applications", "docker", "container"],
    title=Title("Container"),
    attributes={
        "node_name": TextField(Title("Node name")),
    },
)

node_software_applications_docker_containers = Node(
    name="software_applications_docker_containers",
    path=["software", "applications", "docker", "containers"],
    title=Title("Containers"),
    table=Table(
        view=View(name="invdockercontainers", title=Title("Containers")),
        columns={
            "id": TextField(Title("ID")),
            "creation": TextField(Title("Creation")),
            "name": TextField(Title("Name")),
            "labels": TextField(Title("Labels")),
            "status": TextField(Title("Status")),
            "image": TextField(Title("Image")),
        },
    ),
)

node_software_applications_docker_container_networks = Node(
    name="software_applications_docker_container_networks",
    path=["software", "applications", "docker", "container", "networks"],
    title=Title("Networks"),
    table=Table(
        columns={
            "name": TextField(Title("Name")),
            "ip_address": TextField(Title("IP address")),
            "ip_prefixlen": TextField(Title("IP prefix")),
            "gateway": TextField(Title("Gateway")),
            "mac_address": TextField(Title("MAC address")),
            "network_id": TextField(Title("Network ID")),
        },
    ),
)

node_software_applications_docker_container_ports = Node(
    name="software_applications_docker_container_ports",
    path=["software", "applications", "docker", "container", "ports"],
    title=Title("Ports"),
    table=Table(
        columns={
            "port": TextField(Title("Port")),
            "protocol": TextField(Title("Protocol")),
            "host_addresses": TextField(Title("Host addresses")),
        },
    ),
)

node_software_applications_docker_images = Node(
    name="software_applications_docker_images",
    path=["software", "applications", "docker", "images"],
    title=Title("Images"),
    table=Table(
        view=View(name="invdockerimages", title=Title("Images")),
        columns={
            "id": TextField(Title("ID")),
            "creation": TextField(Title("Creation")),
            "size": NumberField(Title("Size"), render=UNIT_BYTES),
            "labels": TextField(Title("Labels")),
            "amount_containers": TextField(Title("#Containers")),
            "repotags": TextField(Title("Repository/Tag")),
            "repodigests": TextField(Title("Digests")),
        },
    ),
)

node_software_applications_docker_networks = Node(
    name="software_applications_docker_networks",
    path=["software", "applications", "docker", "networks"],
    title=Title("Docker networks"),
    table=Table(
        columns={
            "network_id": TextField(Title("Network ID")),
            "short_id": TextField(Title("Short ID")),
            "name": TextField(Title("Name")),
            "scope": TextField(Title("Scope")),
            "labels": TextField(Title("Labels")),
        },
    ),
)

node_software_applications_docker_networks_containers = Node(
    name="software_applications_docker_networks_containers",
    path=["software", "applications", "docker", "networks", "containers"],
    title=Title("Network containers"),
    table=Table(
        columns={
            "network_id": TextField(Title("Network ID")),
            "id": TextField(Title("Container ID")),
            "name": TextField(Title("Name")),
            "ipv4_address": TextField(Title("IPv4 address")),
            "ipv6_address": TextField(Title("IPv6 address")),
            "mac_address": TextField(Title("MAC address")),
        },
    ),
)

node_software_applications_docker_node_labels = Node(
    name="software_applications_docker_node_labels",
    path=["software", "applications", "docker", "node_labels"],
    title=Title("Node labels"),
    table=Table(
        columns={
            "label": TextField(Title("Label")),
        },
    ),
)

node_software_applications_docker_swarm_manager = Node(
    name="software_applications_docker_swarm_manager",
    path=["software", "applications", "docker", "swarm_manager"],
    title=Title("Swarm managers"),
    table=Table(
        columns={
            "NodeID": TextField(Title("Node ID")),
            "Addr": TextField(Title("Address")),
        },
    ),
)
