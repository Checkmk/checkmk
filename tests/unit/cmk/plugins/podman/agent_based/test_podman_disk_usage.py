#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State, StringTable
from cmk.plugins.podman.agent_based.cee.podman_disk_usage import (
    check_podman_disk_usage,
    discover_podman_disk_usage,
    Params,
    parse_podman_disk_usage,
)

STRING_TABLE = [
    [
        '{   "ImagesSize": 8138564,"Images": [{"Repository": "docker.io/library/alpine","Tag": "latest","ImageID": "image_id","Created": "2025-02-14T03:28:36Z","Size": 8132675,"SharedSize": 8132675,"UniqueSize": 0,"Containers": 0},{"Repository": "<none>","Tag": "<none>","ImageID": "image_id3","Created": "2025-05-22T11:43:03.383679101Z","Size": 8123694,"SharedSize": 8123694,"UniqueSize": 0,"Containers": 0},{"Repository": "localhost/rootful-container","Tag": "latest","ImageID": "image_id","Created": "2025-05-22T11:43:03.460453752Z","Size": 8123859,"SharedSize": 8123694,"UniqueSize": 165,"Containers": 2}],"Containers": [{"ContainerID": "con_id1","Image": "image_id","Command": ["sleep","infinity"],"LocalVolumes": 0,"Size": 8135152,"RWSize": 11293,"Created": "2025-05-23T14:54:02.637183731+02:00","Status": "running","Names": "root"},{"ContainerID": "con_id","Image": "image_id","Command": ["sleep","infinity"],"LocalVolumes": 0,"Size": 8135182,"RWSize": 11323,"Created": "2025-06-13T15:22:15.64265355+02:00","Status": "running","Names": "roott"}],"Volumes": []}'
    ],
    [
        '{"ImagesSize": 8160195,"Images": [{"Repository": "docker.io/library/alpine","Tag": "latest","ImageID": "image_id","Created": "2025-02-14T03:28:36Z","Size": 8132675,"SharedSize": 8132675,"UniqueSize": 0,"Containers": 0},{"Repository": "<none>","Tag": "<none>","ImageID": "image_id","Created": "2025-05-22T11:44:00.885199217Z","Size": 8141448,"SharedSize": 8141448,"UniqueSize": 0,"Containers": 0},{"Repository": "<none>","Tag": "<none>","ImageID": "image_id2","Created": "2025-05-22T11:44:00.978371108Z","Size": 8141609,"SharedSize": 8141609,"UniqueSize": 0,"Containers": 0},{"Repository": "localhost/rootless-container","Tag": "latest","ImageID": "image_id1","Created": "2025-05-22T11:44:01.054296201Z","Size": 8141775,"SharedSize": 8141609,"UniqueSize": 166,"Containers": 2}],"Containers": [{"ContainerID": "con_id1","Image": "image_id1","Command": ["sleep","infinity"],"LocalVolumes": 0,"Size": 8152749,"RWSize": 10974,"Created": "2025-06-30T17:22:38.117310829+02:00","Status": "running","Names": "nonroot-test"},{"ContainerID": "con_id2","Image": "image_id1","Command": ["sleep","infinity"],"LocalVolumes": 0,"Size": 8152150,"RWSize": 10375,"Created": "2025-05-23T14:54:46.539802375+02:00","Status": "created","Names": "root"}],"Volumes": [{"VolumeName": "volume1","Links": 0,"Size": 0,"ReclaimableSize": 0}]}'
    ],
]


def test_discover_podman_disk_usage() -> None:
    assert list(discover_podman_disk_usage(parse_podman_disk_usage(STRING_TABLE))) == [
        Service(item="containers"),
        Service(item="images"),
        Service(item="volumes"),
    ]


@pytest.mark.parametrize(
    "string_table, item, params, expected_result",
    [
        pytest.param(
            STRING_TABLE,
            "containers",
            {},
            [
                Result(state=State.OK, summary="Size: 31.1 MiB"),
                Metric(
                    "podman_disk_usage_containers_total_size",
                    32575233.0,
                    boundaries=(0, 32575233.0),
                ),
                Result(state=State.OK, summary="Reclaimable: 42.9 KiB"),
                Metric("podman_disk_usage_containers_reclaimable_size", 43965.0),
                Result(state=State.OK, notice="Total: 4"),
                Metric("podman_disk_usage_containers_total_number", 4.0),
                Result(state=State.OK, notice="Active: 3"),
                Metric("podman_disk_usage_containers_active_number", 3.0),
            ],
            id="Containers with no levels -> OK",
        ),
        pytest.param(
            STRING_TABLE,
            "containers",
            {"containers": {"size_upper": ("fixed", (2000000, 30000000))}},
            [
                Result(state=State.CRIT, summary="Size: 31.1 MiB (warn/crit at 1.91 MiB/28.6 MiB)"),
                Metric(
                    "podman_disk_usage_containers_total_size",
                    32575233.0,
                    levels=(2000000.0, 30000000.0),
                    boundaries=(0, 32575233.0),
                ),
                Result(state=State.OK, summary="Reclaimable: 42.9 KiB"),
                Metric("podman_disk_usage_containers_reclaimable_size", 43965.0),
                Result(state=State.OK, notice="Total: 4"),
                Metric("podman_disk_usage_containers_total_number", 4.0),
                Result(state=State.OK, notice="Active: 3"),
                Metric("podman_disk_usage_containers_active_number", 3.0),
            ],
            id="Containers with size too high -> CRIT",
        ),
        pytest.param(
            STRING_TABLE,
            "containers",
            {"containers": {"active": ("fixed", (2, 5))}},
            [
                Result(state=State.OK, summary="Size: 31.1 MiB"),
                Metric(
                    "podman_disk_usage_containers_total_size",
                    32575233.0,
                    boundaries=(0.0, 32575233.0),
                ),
                Result(state=State.OK, summary="Reclaimable: 42.9 KiB"),
                Metric("podman_disk_usage_containers_reclaimable_size", 43965.0),
                Result(state=State.OK, notice="Total: 4"),
                Metric("podman_disk_usage_containers_total_number", 4.0),
                Result(state=State.WARN, summary="Active: 3 (warn/crit at 2/5)"),
                Metric("podman_disk_usage_containers_active_number", 3.0, levels=(2.0, 5.0)),
            ],
            id="Too many active containers -> WARN",
        ),
        pytest.param(
            STRING_TABLE,
            "images",
            {},
            [
                Result(state=State.OK, summary="Size: 54.3 MiB"),
                Metric(
                    "podman_disk_usage_images_total_size", 56937735.0, boundaries=(0.0, 56937735.0)
                ),
                Result(state=State.OK, notice="Total: 7"),
                Metric("podman_disk_usage_images_total_number", 7.0),
                Result(state=State.OK, notice="Active: 2"),
                Metric("podman_disk_usage_images_active_number", 2.0),
            ],
            id="Images with no levels -> OK",
        ),
        pytest.param(
            STRING_TABLE,
            "images",
            {"images": {"total": ("fixed", (2, 5))}},
            [
                Result(state=State.OK, summary="Size: 54.3 MiB"),
                Metric(
                    "podman_disk_usage_images_total_size", 56937735.0, boundaries=(0.0, 56937735.0)
                ),
                Result(state=State.CRIT, summary="Total: 7 (warn/crit at 2/5)"),
                Metric("podman_disk_usage_images_total_number", 7.0, levels=(2.0, 5.0)),
                Result(state=State.OK, notice="Active: 2"),
                Metric("podman_disk_usage_images_active_number", 2.0),
            ],
            id="Too many images -> CRIT",
        ),
        pytest.param(
            STRING_TABLE,
            "volumes",
            {},
            [
                Result(state=State.OK, summary="Size: 0 B"),
                Metric("podman_disk_usage_volumes_total_size", 0.0, boundaries=(0, 0)),
                Result(state=State.OK, summary="Reclaimable: 0 B"),
                Metric("podman_disk_usage_volumes_reclaimable_size", 0.0),
                Result(state=State.OK, notice="Total: 1"),
                Metric("podman_disk_usage_volumes_total_number", 1.0),
                Result(state=State.OK, notice="Active: 0"),
                Metric("podman_disk_usage_volumes_active_number", 0.0),
            ],
            id="Volumes with no levels -> OK",
        ),
    ],
)
def test_check_podman_disk_usage(
    string_table: StringTable, item: str, params: Params, expected_result: CheckResult
) -> None:
    assert (
        list(check_podman_disk_usage(item, params, parse_podman_disk_usage(string_table)))
        == expected_result
    )
