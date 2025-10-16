#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.agent_based.v2 import Attributes, InventoryResult, TableRow
from cmk.plugins.podman.agent_based.cee.inventory_podman import inventory_podman
from cmk.plugins.podman.agent_based.cee.lib import SectionPodmanEngineStats
from cmk.plugins.podman.agent_based.cee.podman_containers import (
    Container,
    ContainerStateCounts,
    SectionContainers,
)
from cmk.plugins.podman.agent_based.cee.podman_disk_usage import DiskUsage, Entity, EntityGroup
from cmk.plugins.podman.agent_based.cee.podman_disk_usage import Section as DiskUsageSection

SECTION_PODMAN_ENGINE = SectionPodmanEngineStats.model_validate(
    {
        "version": {
            "APIVersion": "4.9.3",
        },
        "host": {
            "security": {
                "rootless": True,
            },
            "hostname": "podman-host",
        },
        "registries": {},
    }
)
SECTION_PODMAN_CONTAINERS = SectionContainers(
    containers=[
        Container(
            Id="50baa2b53cb3548c717526bd80eca26e5d525f3f7a2479f06f3eab88d5332053",
            State="running",
            ExitCode=0,
            Status="",
            Created="2025-05-23T14:54:02.637183731+02:00",
            Names=["root"],
            Image="localhost/rootful-container:latest",
            Labels={"io.buildah.version": "1.33.7"},
        ),
        Container(
            Id="63f10448c71cd61479ed6edf515bf45486f2e3b0008f873920ecc2c9008e7276",
            State="running",
            ExitCode=0,
            Status="",
            Created="2025-06-30T17:22:38.117310829+02:00",
            Names=["nonroot-test"],
            Image="localhost/rootless-container:latest",
            Labels={"io.buildah.version": "1.33.7"},
        ),
    ],
    counts=ContainerStateCounts(
        total=2,
        running=2,
        created=0,
        paused=0,
        stopped=0,
        restarting=0,
        removing=0,
        dead=0,
        exited=0,
        exited_as_non_zero=0,
    ),
)
SECTION_PODMAN_DISK_USAGE = DiskUsageSection(
    images=EntityGroup(
        items=[
            Entity(
                id="aded1e1a5b3705116fa0a92ba074a5e0b0031647d9c315983ccba2ee5428ec8b",
                size=8132675.0,
                active=False,
                reclaimable_size=None,
                creation="2025-02-14T03:28:36Z",
                repository="docker.io/library/alpine",
                tag="latest",
                containers=0,
            ),
            Entity(
                id="b94a67d30b3c46916d36bda349ecc9bdef11ff9c90bb55e514575488c3726617",
                size=8123859.0,
                active=True,
                reclaimable_size=None,
                creation="2025-05-22T11:43:03.460453752Z",
                repository="localhost/rootful-container",
                tag="latest",
                containers=2,
            ),
        ]
    ),
    disk_usage={
        "containers": DiskUsage(
            size=16270334.0, reclaimable_size=22616.0, total_number=2, active_number=2
        ),
        "images": DiskUsage(
            size=24380228.0, reclaimable_size=None, total_number=2, active_number=1
        ),
        "volumes": DiskUsage(size=0, reclaimable_size=0, total_number=0, active_number=0),
    },
)


@pytest.mark.parametrize(
    "section_podman_engine, section_podman_containers, section_podman_disk_usage, expected_result",
    [
        pytest.param(
            SECTION_PODMAN_ENGINE,
            SECTION_PODMAN_CONTAINERS,
            SECTION_PODMAN_DISK_USAGE,
            [
                Attributes(
                    path=["software", "applications", "podman"],
                    inventory_attributes={
                        "mode": "Rootless",
                        "version": "4.9.3",
                        "registry": "{}",
                        "containers_running": 2,
                        "containers_paused": 0,
                        "containers_stopped": 0,
                        "containers_exited": 0,
                        "images_num": 2,
                    },
                    status_attributes={},
                ),
                TableRow(
                    path=["software", "applications", "podman", "containers"],
                    key_columns={
                        "id": "50baa2b53cb3548c717526bd80eca26e5d525f3f7a2479f06f3eab88d5332053"
                    },
                    inventory_columns={
                        "creation": 1748004842.637183,
                        "name": "root",
                        "labels": "io.buildah.version=1.33.7",
                        "status": "running",
                        "image": "localhost/rootful-container:latest",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["software", "applications", "podman", "containers"],
                    key_columns={
                        "id": "63f10448c71cd61479ed6edf515bf45486f2e3b0008f873920ecc2c9008e7276"
                    },
                    inventory_columns={
                        "creation": 1751296958.11731,
                        "name": "nonroot-test",
                        "labels": "io.buildah.version=1.33.7",
                        "status": "running",
                        "image": "localhost/rootless-container:latest",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["software", "applications", "podman", "images"],
                    key_columns={
                        "id": "aded1e1a5b3705116fa0a92ba074a5e0b0031647d9c315983ccba2ee5428ec8b"
                    },
                    inventory_columns={
                        "creation": 1739503716.0,
                        "size": 8132675.0,
                        "container_num": 0,
                        "repository": "docker.io/library/alpine",
                        "tag": "latest",
                    },
                    status_columns={},
                ),
                TableRow(
                    path=["software", "applications", "podman", "images"],
                    key_columns={
                        "id": "b94a67d30b3c46916d36bda349ecc9bdef11ff9c90bb55e514575488c3726617"
                    },
                    inventory_columns={
                        "creation": 1747914183.460453,
                        "size": 8123859.0,
                        "container_num": 2,
                        "repository": "localhost/rootful-container",
                        "tag": "latest",
                    },
                    status_columns={},
                ),
            ],
            id="Everything present -> Attributes yielded",
        ),
        pytest.param(
            None,
            SECTION_PODMAN_CONTAINERS,
            SECTION_PODMAN_DISK_USAGE,
            [],
            id="One of the sections is None -> No result",
        ),
    ],
)
def test_inventory_podman(
    section_podman_engine: SectionPodmanEngineStats | None,
    section_podman_containers: SectionContainers | None,
    section_podman_disk_usage: DiskUsageSection | None,
    expected_result: InventoryResult,
) -> None:
    assert (
        list(
            inventory_podman(
                section_podman_engine,
                section_podman_containers,
                section_podman_disk_usage,
            )
        )
        == expected_result
    )
