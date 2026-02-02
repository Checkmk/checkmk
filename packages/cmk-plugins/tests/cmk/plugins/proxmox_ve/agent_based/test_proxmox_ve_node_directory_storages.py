#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State
from cmk.plugins.proxmox_ve.agent_based.proxmox_ve_node_directory_storages import (
    discover_proxmox_ve_node_directory_storage,
)
from cmk.plugins.proxmox_ve.lib.node_storages import (
    check_proxmox_ve_node_storage,
    SectionNodeStorages,
    Storage,
    StorageLink,
)

SECTION = SectionNodeStorages(
    node="pve-node1",
    storages=[
        Storage.model_validate(
            {
                "node": "pve-node1",
                "disk": 17737418240.0,
                "maxdisk": 21474836480.0,
                "plugintype": "dir",
                "status": "active",
                "storage": "local",
            }
        ),
        Storage.model_validate(
            {
                "node": "pve-node1",
                "disk": 5368709120.0,
                "maxdisk": 10737418240.0,
                "plugintype": "pbs",
                "status": "unknown",
                "storage": "data",
            }
        ),
        Storage.model_validate(
            {
                "node": "pve-node1",
                "disk": 3221225472.0,
                "maxdisk": 6442450944.0,
                "plugintype": "nfs",
                "status": "active",
                "storage": "nfs-storage",
            }
        ),
        Storage.model_validate(
            {
                "node": "pve1",
                "disk": 212992.0,
                "maxdisk": 19799465984.0,
                "plugintype": "zfspool",
                "status": "available",
                "storage": "local-zfs",
            }
        ),
    ],
    storage_links={
        "local-zfs": [
            StorageLink(type="scsi0", size="16G", vmid="101"),
            StorageLink(type="scsi0", size="16G", vmid="100"),
        ],
    },
)


def test_discover_proxmox_ve_node_directory_storage() -> None:
    assert list(discover_proxmox_ve_node_directory_storage(SECTION)) == [
        Service(item="local"),
        Service(item="data"),
        Service(item="local-zfs"),
    ]


@pytest.mark.parametrize(
    "item,params,section,expected_results",
    [
        pytest.param(
            "local",
            {"levels": (95.0, 100.0)},
            SECTION,
            [
                Metric(
                    "fs_used",
                    16915.72021484375,
                    levels=(19456.0, 20480.0),
                    boundaries=(0.0, 20480.0),
                ),
                Metric("fs_free", 3564.27978515625, boundaries=(0.0, None)),
                Metric(
                    "fs_used_percent",
                    82.59629011154175,
                    levels=(95.0, 100.0),
                    boundaries=(0.0, 100.0),
                ),
                Result(
                    state=State.OK,
                    summary="Used: 82.60% - 16.5 GiB of 20.0 GiB",
                ),
                Metric("fs_size", 20480.0, boundaries=(0.0, None)),
                Result(state=State.OK, summary="Type: dir"),
            ],
            id="Everything OK",
        ),
        pytest.param(
            "local",
            {"levels": (80.0, 90.0)},
            SECTION,
            [
                Metric(
                    "fs_used",
                    16915.72021484375,
                    levels=(16384.0, 18432.0),
                    boundaries=(0.0, 20480.0),
                ),
                Metric("fs_free", 3564.27978515625, boundaries=(0.0, None)),
                Metric(
                    "fs_used_percent",
                    82.59629011154175,
                    levels=(80.0, 90.0),
                    boundaries=(0.0, 100.0),
                ),
                Result(
                    state=State.WARN,
                    summary="Used: 82.60% - 16.5 GiB of 20.0 GiB (warn/crit at 80.00%/90.00% used)",
                ),
                Metric("fs_size", 20480.0, boundaries=(0.0, None)),
                Result(state=State.OK, summary="Type: dir"),
            ],
            id="WARN, with levels",
        ),
        pytest.param(
            "data",
            {"levels": (80.0, 90.0)},
            SECTION,
            [
                Result(
                    state=State.WARN,
                    summary="Storage status is unknown. Skipping filesystem check.",
                )
            ],
            id="WARN, because the storage is not active or available",
        ),
        pytest.param(
            "local-zfs",
            {"levels": (80.0, 90.0)},
            SECTION,
            [
                Metric(
                    "fs_used",
                    0.203125,
                    levels=(15105.793749809265, 16994.017968177795),
                    boundaries=(0.0, 18882.2421875),
                ),
                Metric("fs_free", 18882.0390625, boundaries=(0.0, None)),
                Metric(
                    "fs_used_percent",
                    0.0010757461851350909,
                    levels=(79.99999999898988, 89.99999999696962),
                    boundaries=(0.0, 100.0),
                ),
                Result(state=State.OK, summary="Used: <0.01% - 208 KiB of 18.4 GiB"),
                Metric("fs_size", 18882.2421875, boundaries=(0.0, None)),
                Result(state=State.OK, summary="Type: zfspool"),
                Result(state=State.OK, summary="Provisioned: 32.0 GiB"),
                Metric("provisioned_storage_space", 32768.0),
                Result(state=State.OK, summary="Provisioning: 173.54%"),
                Metric("provisioned_storage_usage", 173.54),
                Result(state=State.OK, summary="Uncommitted: 0 B"),
                Metric("uncommitted", 0.0),
            ],
            id="OK, with storage links",
        ),
    ],
)
def test_check_proxmox_ve_node_directory_storages(
    item: str,
    params: Mapping[str, object],
    section: SectionNodeStorages,
    expected_results: CheckResult,
) -> None:
    assert (
        list(
            check_proxmox_ve_node_storage(
                item=item,
                params=params,
                section=section.directory_storages,
                storage_links=section.storage_links,
                value_store={},
            )
        )
        == expected_results
    )
