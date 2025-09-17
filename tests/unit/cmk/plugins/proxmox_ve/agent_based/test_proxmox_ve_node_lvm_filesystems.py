#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State
from cmk.plugins.proxmox_ve.agent_based.proxmox_ve_node_lvm_filesystems import (
    discover_proxmox_ve_node_lvm_filesystem,
)
from cmk.plugins.proxmox_ve.lib.node_filesystems import (
    check_proxmox_ve_node_filesystems,
    SectionNodeFilesystems,
    Storage,
)

SECTION = SectionNodeFilesystems(
    node="pve-node1",
    filesystems=[
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
                "disk": 9968709120.0,
                "maxdisk": 10737418240.0,
                "plugintype": "lvmthin",
                "status": "active",
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


def test_discover_proxmox_ve_node_lvm_filesystem() -> None:
    assert list(discover_proxmox_ve_node_lvm_filesystem(SECTION)) == [Service(item="data")]


@pytest.mark.parametrize(
    "params,section,expected_results",
    [
        pytest.param(
            {"levels": (95.0, 100.0)},
            SECTION,
            [
                Metric(
                    "fs_used", 9506.90185546875, levels=(9728.0, 10240.0), boundaries=(0.0, 10240.0)
                ),
                Metric("fs_free", 733.09814453125, boundaries=(0.0, None)),
                Metric(
                    "fs_used_percent",
                    92.84083843231201,
                    levels=(95.0, 100.0),
                    boundaries=(0.0, 100.0),
                ),
                Result(state=State.OK, summary="Used: 92.84% - 9.28 GiB of 10.0 GiB"),
                Metric("fs_size", 10240.0, boundaries=(0.0, None)),
                Result(state=State.OK, summary="Type: lvmthin"),
            ],
            id="Everything OK",
        ),
        pytest.param(
            {
                "levels": (80.0, 90.0),
            },
            SECTION,
            [
                Metric(
                    "fs_used", 9506.90185546875, levels=(8192.0, 9216.0), boundaries=(0.0, 10240.0)
                ),
                Metric("fs_free", 733.09814453125, boundaries=(0.0, None)),
                Metric(
                    "fs_used_percent",
                    92.84083843231201,
                    levels=(80.0, 90.0),
                    boundaries=(0.0, 100.0),
                ),
                Result(
                    state=State.CRIT,
                    summary="Used: 92.84% - 9.28 GiB of 10.0 GiB (warn/crit at 80.00%/90.00% used)",
                ),
                Metric("fs_size", 10240.0, boundaries=(0.0, None)),
                Result(state=State.OK, summary="Type: lvmthin"),
            ],
            id="WARN, with levels",
        ),
    ],
)
def test_check_proxmox_ve_node_info(
    params: Mapping[str, object],
    section: SectionNodeFilesystems,
    expected_results: CheckResult,
) -> None:
    assert (
        list(
            check_proxmox_ve_node_filesystems(
                item="data",
                params=params,
                section=section.lvm_filesystems,
                value_store={},
            )
        )
        == expected_results
    )
