#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, MutableMapping, Sequence
from enum import StrEnum
from typing import Any

from pydantic import AliasChoices, BaseModel, Field

from cmk.agent_based.v2 import check_levels, CheckResult, render, Result, State
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


def _transform_storage_size_bytes_to_mb(storage_size: float) -> float:
    return storage_size / (1024 * 1024)


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

    @property
    def bytes_size(self) -> float | None:
        size_str = self.size.upper()
        if size_str.endswith("G"):
            return float(size_str[:-1]) * 1024**3
        if size_str.endswith("M"):
            return float(size_str[:-1]) * 1024**2
        if size_str.endswith("K"):
            return float(size_str[:-1]) * 1024
        if size_str.endswith("T"):
            return float(size_str[:-1]) * 1024**4
        try:
            return float(size_str)
        except ValueError:
            return None


class SectionNodeStorages(BaseModel, frozen=True):
    node: str
    storages: Sequence[Storage]
    storage_links: Mapping[str, Sequence[StorageLink]] = {}

    @property
    def directory_storages(self) -> Mapping[str, Storage]:
        return {
            storage.name: storage
            for storage in self.storages
            if storage.storage_type
            in (
                StorageType.DIR,
                StorageType.PBS,
                StorageType.ZFS,
                StorageType.ZFSPOOL,
            )
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
    storage_links: Mapping[str, Sequence[StorageLink]],
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
        filesystem_size=_transform_storage_size_bytes_to_mb(storage.maxdisk)
        if storage.maxdisk is not None
        else None,
        free_space=(
            _transform_storage_size_bytes_to_mb(storage.maxdisk - storage.disk)
            if storage.disk is not None and storage.maxdisk is not None
            else None
        ),
        reserved_space=0.0,
        inodes_avail=None,
        inodes_total=None,
        params=params,
    )
    yield Result(state=State.OK, summary=f"Type: {storage.storage_type}")
    yield from _check_proxmox_ve_node_storage_provision(
        item=item,
        storage_max_disk=_transform_storage_size_bytes_to_mb(storage.maxdisk)
        if storage.maxdisk
        else None,
        storage_links=storage_links,
    )


def _check_proxmox_ve_node_storage_provision(
    item: str,
    storage_max_disk: float | None,
    storage_links: Mapping[str, Sequence[StorageLink]],
) -> CheckResult:
    if (storage := storage_links.get(item)) is None:
        return

    if storage_max_disk is None or storage_max_disk <= 0:
        yield Result(
            state=State.WARN,
            summary="Cannot calculate committed space as storage max disk is unknown or zero.",
        )
        return

    committed = _transform_storage_size_bytes_to_mb(
        sum(link.bytes_size for link in storage if link.bytes_size is not None)
    )
    uncommitted_mb = (storage_max_disk - committed) if storage_max_disk > committed else 0
    yield from check_levels(
        value=uncommitted_mb,
        metric_name="uncommitted",
        label="Uncommitted",
        render_func=lambda v: render.bytes(v * 1024 * 1024),
    )

    provisioned_percent = round((committed / storage_max_disk) * 100, 2)
    yield from check_levels(
        value=provisioned_percent,
        metric_name="provisioned_storage_usage",
        label="Provisioning",
        render_func=render.percent,
    )
