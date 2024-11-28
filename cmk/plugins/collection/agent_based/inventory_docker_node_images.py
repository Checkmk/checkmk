#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping

from cmk.agent_based.v2 import AgentSection, InventoryPlugin, InventoryResult, StringTable, TableRow
from cmk.plugins.lib import docker

Section = Mapping[str, Mapping]


def parse_docker_node_images(string_table: StringTable) -> Section:
    docker.ensure_valid_docker_header(string_table)

    subsections = _split_subsections(string_table[1:])
    i_images = (json.loads(i[0]) for i in subsections.get("images", []))
    images = {i["Id"]: i for i in i_images if i is not None}
    i_containers = (json.loads(c[0]) for c in subsections.get("containers", []))
    containers = {c["Id"]: c for c in i_containers if c is not None}

    running_images = [c["Image"] for c in containers.values()]

    for image_id, image in images.items():
        image["amount_containers"] = running_images.count(image_id)

    return {"images": images, "containers": containers}


def _split_subsections(string_table: StringTable) -> dict[str, list[list[str]]]:
    subname = ""
    subsections: dict[str, list[list[str]]] = {}
    for row in string_table:
        if not row:
            continue
        if row[0].startswith("[[[") and row[0].endswith("]]]"):
            subname = row[0].strip("[]")
            continue
        subsections.setdefault(subname, []).append(row)
    return subsections


agent_section_docker_node_images = AgentSection(
    name="docker_node_images",
    parse_function=parse_docker_node_images,
)


def inventory_docker_node_images(section: Section) -> InventoryResult:
    images = section.get("images", {})
    for image_id, image in sorted(images.items()):
        repodigests = ", ".join(image.get("RepoDigests", []))
        fallback_repotag = repodigests.split("@", 1)[:1] if "@" in repodigests else []
        yield TableRow(
            path=["software", "applications", "docker", "images"],
            key_columns={
                "id": docker.get_short_id(image_id),
            },
            inventory_columns={
                "repotags": ", ".join(image.get("RepoTags", fallback_repotag)),
                "repodigests": repodigests,
                "creation": image["Created"],
                "size": image.get("VirtualSize", image.get("Size")),
                "labels": docker.format_labels(image.get("Config", {}).get("Labels") or {}),
            },
            status_columns={
                "amount_containers": image["amount_containers"],
            },
        )

    containers = section.get("containers", {})
    for container_id, container in sorted(containers.items()):
        yield TableRow(
            path=["software", "applications", "docker", "containers"],
            key_columns={
                "id": docker.get_short_id(container_id),
            },
            inventory_columns={},
            status_columns={
                "image": docker.get_short_id(container["Image"]),
                "name": container["Name"],
                "creation": container["Created"],
                "labels": docker.format_labels(container.get("Config", {}).get("Labels", {})),
                "status": container.get("State", {}).get("Status"),
            },
        )


inventory_plugin_docker_node_images = InventoryPlugin(
    name="docker_node_images",
    inventory_function=inventory_docker_node_images,
)
