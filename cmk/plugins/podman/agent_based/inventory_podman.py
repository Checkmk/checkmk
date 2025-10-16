#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime

from cmk.agent_based.v2 import Attributes, InventoryPlugin, InventoryResult, TableRow

from .lib import SectionPodmanEngineStats
from .podman_containers import Container, SectionContainers
from .podman_disk_usage import Entity
from .podman_disk_usage import Section as DiskUsageSection


def _container_to_table(container: Container) -> TableRow:
    return TableRow(
        path=["software", "applications", "podman", "containers"],
        key_columns={"id": container.Id},
        inventory_columns={
            "creation": datetime.fromisoformat(container.creation).timestamp(),
            "name": container.name[0].strip("/") if container.name else "unnamed",
            "labels": (",".join(f"{k}={v}" for k, v in container.labels.items()))
            if container.labels
            else "",
            "status": container.State,
            "image": container.image,
        },
    )


def _image_to_table(image: Entity) -> TableRow:
    return TableRow(
        path=["software", "applications", "podman", "images"],
        key_columns={"id": image.id},
        inventory_columns={
            "creation": datetime.fromisoformat(image.creation).timestamp()
            if image.creation
            else "",
            "size": image.size,
            "container_num": image.containers or 0,
            "repository": image.repository or "",
            "tag": image.tag or "",
        },
    )


def inventory_podman(
    section_podman_engine: SectionPodmanEngineStats | None,
    section_podman_containers: SectionContainers | None,
    section_podman_disk_usage: DiskUsageSection | None,
) -> InventoryResult:
    if (
        section_podman_engine is None
        or section_podman_containers is None
        or section_podman_disk_usage is None
    ):
        return

    yield Attributes(
        path=["software", "applications", "podman"],
        inventory_attributes={
            "mode": "Rootless" if section_podman_engine.rootless else "Rootful",
            "version": section_podman_engine.api_version,
            "registry": str(section_podman_engine.registries),
            "containers_running": section_podman_containers.counts.running,
            "containers_paused": section_podman_containers.counts.paused,
            "containers_stopped": section_podman_containers.counts.stopped,
            "containers_exited": section_podman_containers.counts.exited,
            "images_num": section_podman_disk_usage.disk_usage["images"].total_number,
        },
    )

    yield from (
        _container_to_table(container) for container in section_podman_containers.containers
    )
    yield from (_image_to_table(image) for image in section_podman_disk_usage.images.items)


inventory_plugin_podman = InventoryPlugin(
    name="inventory_podman",
    sections=[
        "podman_engine",
        "podman_containers",
        "podman_disk_usage",
    ],
    inventory_function=inventory_podman,
)
