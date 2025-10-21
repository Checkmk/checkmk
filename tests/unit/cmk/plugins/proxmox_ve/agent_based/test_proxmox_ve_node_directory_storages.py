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
    ],
)


def test_discover_proxmox_ve_node_directory_storage() -> None:
    assert list(discover_proxmox_ve_node_directory_storage(SECTION)) == [
        Service(item="local"),
        Service(item="data"),
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
    ],
)
def test_check_proxmox_ve_node_info(
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
                value_store={},
            )
        )
        == expected_results
    )
