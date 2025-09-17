#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, MutableMapping, Sequence
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from cmk.agent_based.v2 import CheckResult, Result, State
from cmk.plugins.lib.df import df_check_filesystem_single


class StorageType(StrEnum):
    BTRFS = "btrfs"
    CEPHFS = "cephfs"
    CIFS = "cifs"
    DIR = "dir"
    ESXI = "esxi"
    ISCSI = "iscsi"
    ISCSIDIRECT = "iscsidirect"
    LVM = "lvm"
    LVMTHIN = "lvmthin"
    NFS = "nfs"
    PBS = "pbs"
    RBD = "rbd"
    ZFS = "zfs"
    ZFSPOOL = "zfspool"


class Storage(BaseModel, frozen=True):
    node: str
    disk: float
    maxdisk: float
    storage_type: StorageType = Field(alias="plugintype")
    status: str
    name: str = Field(alias="storage")


class SectionNodeFilesystems(BaseModel, frozen=True):
    node: str
    filesystems: Sequence[Storage]

    @property
    def directory_filesystems(self) -> Mapping[str, Storage]:
        return {
            filesystem.name: filesystem
            for filesystem in self.filesystems
            if filesystem.storage_type == StorageType.DIR
        }

    @property
    def lvm_filesystems(self) -> Mapping[str, Storage]:
        return {
            filesystem.name: filesystem
            for filesystem in self.filesystems
            if filesystem.storage_type in (StorageType.LVM, StorageType.LVMTHIN)
        }


def check_proxmox_ve_node_filesystems(
    item: str,
    params: Mapping[str, Any],
    section: Mapping[str, Storage],
    value_store: MutableMapping[str, Any],
) -> CheckResult:
    if (filesystem := section.get(item)) is None:
        return

    yield from df_check_filesystem_single(
        value_store=value_store,
        mountpoint=item,
        filesystem_size=filesystem.maxdisk / (1024 * 1024),
        free_space=(filesystem.maxdisk - filesystem.disk) / (1024 * 1024),
        reserved_space=0.0,
        inodes_avail=None,
        inodes_total=None,
        params=params,
    )
    yield Result(state=State.OK, summary=f"Type: {filesystem.storage_type}")
