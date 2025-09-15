#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from enum import StrEnum

from pydantic import BaseModel, Field


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
