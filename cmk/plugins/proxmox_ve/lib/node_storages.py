#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, MutableMapping, Sequence
from enum import StrEnum
from typing import Any

from pydantic import AliasChoices, BaseModel, Field

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


class StorageStatus(StrEnum):
    AVAILABLE = "available"
    ENABLED = "enabled"
    DISABLED = "disabled"
    INACTIVE = "inactive"
    UNKNOWN = "unknown"
    OFFLINE = "offline"
    ERROR = "error"
    MAINTENANCE = "maintenance"
    ACTIVE = "active"


class Storage(BaseModel, frozen=True):
    node: str
    disk: float | None = None
    maxdisk: float | None = None
    storage_type: StorageType = Field(
        alias="storage_type",
        validation_alias=AliasChoices("plugintype", "storage_type"),
    )
    status: StorageStatus | None = None
    name: str = Field(alias="name", validation_alias=AliasChoices("storage", "name"))


class StorageLink(BaseModel, frozen=True):
    type: str
    size: str
    vmid: str


class SectionNodeStorages(BaseModel, frozen=True):
    node: str
    storages: Sequence[Storage]
    storage_links: Mapping[str, Sequence[StorageLink]] = {}

    @property
    def directory_storages(self) -> Mapping[str, Storage]:
        return {
            storage.name: storage
            for storage in self.storages
            if storage.storage_type in (StorageType.DIR, StorageType.PBS)
        }

    @property
    def lvm_storages(self) -> Mapping[str, Storage]:
        return {
            storage.name: storage
            for storage in self.storages
            if storage.storage_type in (StorageType.LVM, StorageType.LVMTHIN)
        }


def check_proxmox_ve_node_storage(
    item: str,
    params: Mapping[str, Any],
    section: Mapping[str, Storage],
    value_store: MutableMapping[str, Any],
) -> CheckResult:
    if (storage := section.get(item)) is None:
        return

    if storage.status not in (StorageStatus.AVAILABLE, StorageStatus.ACTIVE):
        yield Result(
            state=State.WARN,
            summary=f"Storage status is {storage.status}. Skipping filesystem check.",
        )
        return

    yield from df_check_filesystem_single(
        value_store=value_store,
        mountpoint=item,
        filesystem_size=(storage.maxdisk / (1024 * 1024)) if storage.maxdisk is not None else None,
        free_space=((storage.maxdisk - storage.disk) / (1024 * 1024))
        if storage.disk is not None and storage.maxdisk is not None
        else None,
        reserved_space=0.0,
        inodes_avail=None,
        inodes_total=None,
        params=params,
    )
    yield Result(state=State.OK, summary=f"Type: {storage.storage_type}")
