#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.inventory_ui.v1_unstable import (
    DecimalNotation,
    Node,
    NumberField,
    StrictPrecision,
    Table,
    TextField,
    Title,
    Unit,
)

UNIT_COUNT = Unit(DecimalNotation(""), StrictPrecision(0))

node_software_applications_podman = Node(
    name="software_applications_podman",
    path=["software", "applications", "podman"],
    title=Title("Podman"),
    attributes={
        "mode": TextField(Title("Mode")),
        "version": TextField(Title("Version")),
        "registry": TextField(Title("Registry")),
        "containers_running": NumberField(Title("#Containers running"), render=UNIT_COUNT),
        "containers_paused": NumberField(Title("#Containers paused"), render=UNIT_COUNT),
        "containers_stopped": NumberField(Title("#Containers stopped"), render=UNIT_COUNT),
        "containers_exited": NumberField(Title("#Containers exited"), render=UNIT_COUNT),
        "images_num": NumberField(Title("#Images"), render=UNIT_COUNT),
    },
)

node_software_applications_podman_containers = Node(
    name="software_applications_podman_containers",
    path=["software", "applications", "podman", "containers"],
    title=Title("Containers"),
    table=Table(
        columns={
            "id": TextField(Title("ID")),
            "creation": TextField(Title("Creation")),
            "name": TextField(Title("Name")),
            "labels": TextField(Title("Labels")),
            "status": TextField(Title("Status")),
            "image": TextField(Title("Image")),
        }
    ),
)

node_software_applications_podman_images = Node(
    name="software_applications_podman_images",
    path=["software", "applications", "podman", "images"],
    title=Title("Images"),
    table=Table(
        columns={
            "id": TextField(Title("ID")),
            "creation": TextField(Title("Creation")),
            "size": TextField(Title("Size")),
            "container_num": NumberField(Title("#Containers"), render=UNIT_COUNT),
            "repository": TextField(Title("Repository")),
            "tag": TextField(Title("Tag")),
        },
    ),
)

node_software_applications_podman_container = Node(
    name="software_applications_podman_container",
    path=["software", "applications", "podman", "container"],
    title=Title("Container"),
    attributes={
        "hostname": TextField(Title("Host name")),
        "pod": TextField(Title("Pod")),
        "labels": TextField(Title("Labels")),
    },
)

node_software_applications_podman_network = Node(
    name="software_applications_podman_network",
    path=["software", "applications", "podman", "network"],
    title=Title("Network"),
    attributes={
        "ip_address": TextField(Title("IP address")),
        "gateway": TextField(Title("Gateway")),
        "mac_address": TextField(Title("MAC address")),
    },
)
