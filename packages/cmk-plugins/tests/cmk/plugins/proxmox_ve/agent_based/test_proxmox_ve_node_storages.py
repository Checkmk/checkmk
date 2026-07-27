#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json

from cmk.plugins.proxmox_ve.agent_based.proxmox_ve_node_storages import (
    parse_proxmox_ve_node_storage,
)
from cmk.plugins.proxmox_ve.lib.node_storages import SectionNodeStorages, Storage, StorageLink


def _string_table(raw: object) -> list[list[str]]:
    return [[json.dumps(raw)]]


def test_parse_proxmox_ve_node_storage() -> None:
    raw = {
        "node": "pve-node1",
        "storages": [
            {
                "node": "pve-node1",
                "disk": 1.0,
                "maxdisk": 2.0,
                "plugintype": "dir",
                "status": "active",
                "storage": "local",
            },
        ],
        "vm_disks": [
            {"vmid": "100", "disks": {"scsi0": "local-zfs:vm-100-disk-0,size=16G"}},
            {"vmid": "101", "disks": {"scsi0": "local-zfs:vm-101-disk-0,size=16G"}},
            {"vmid": "137", "disks": {"rootfs": "local:vm-137-disk-0,size=8G"}},
        ],
    }

    assert parse_proxmox_ve_node_storage(_string_table(raw)) == SectionNodeStorages(
        node="pve-node1",
        storages=[
            Storage.model_validate(
                {
                    "node": "pve-node1",
                    "disk": 1.0,
                    "maxdisk": 2.0,
                    "plugintype": "dir",
                    "status": "active",
                    "storage": "local",
                }
            ),
        ],
        storage_links={
            "local-zfs": [
                StorageLink(type="scsi0", size="16G", vmid="100"),
                StorageLink(type="scsi0", size="16G", vmid="101"),
            ],
            "local": [
                StorageLink(type="rootfs", size="8G", vmid="137"),
            ],
        },
    )


def test_parse_proxmox_ve_node_storage_no_vm_disks() -> None:
    raw = {"node": "pve-node1", "storages": [], "vm_disks": []}

    assert parse_proxmox_ve_node_storage(_string_table(raw)) == SectionNodeStorages(
        node="pve-node1",
        storages=[],
        storage_links={},
    )
