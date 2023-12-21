#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


"""Wrapper from marshmallow based NetApp-Python-Library pydantic Checkmk-NetApp-Protocol
There is no real logic in here, just filtering, type hinting, validating, restructuring.

Docs:
- https://github.com/NetApp/ontap-rest-python
- https://library.netapp.com/ecmdocs/ECMLP2885799/html/index.html#/
- https://library.netapp.com/ecmdocs/ECMLP2885777/html/resources/counter_table.html
- https://docs.netapp.com/us-en/ontap-restmap-9131//perf.html#perf-object-instance-list-info-iter
"""
from pydantic import BaseModel

MEGA = 1024 * 1024


class VolumeModel(BaseModel):
    """
    api: /api/storage/volumes
    doc: https://docs.netapp.com/us-en/ontap-restmap-9131//volume.html#volume-footprint-get-iter
    call: next(NetAppResource.Volume.get_collection(fields="*"))

    ============
    OLD -> NEW:
    ============
    "volume-space-attributes.size-available" -> space.available
    "volume-space-attributes.size-total" -> space.afs_total
    "volume-space-attributes.is-space-enforcement-logical" -> space.logical_space.enforcement
    "volume-space-attributes.logical-used" -> space.logical_space.used

    "volume-state-attributes.state" -> state

    "volume-id-attributes.instance-uuid" -> uuid
    "volume-id-attributes.owning-vserver-name" -> svm.name
    "volume-id-attributes.name" -> name
    "volume-id-attributes.node" -> NA  # ! missing in the new API
    "volume-id-attributes.msid" -> msid

    "volume-inode-attributes.files-total" -> files.maximum
    "volume-inode-attributes.files-used" -> files.used
    ============

    """

    uuid: str
    state: str | None = None
    name: str
    msid: int
    space_available: int | None = None  # None because sometime this data is not present
    space_total: int | None = None  # None because sometime this data is not present
    logical_enforcement: bool | None = None  # None because sometime this data is not present
    logical_used: int | None = None  # None because sometime this data is not present
    svm_name: str
    svm_uuid: str
    files_maximum: int | None = None  # None because sometime this data is not present
    files_used: int | None = None  # None because sometime this data is not present

    def size_total(self) -> float | None:
        return self.space_total / MEGA if self.space_total is not None else None

    def size_available(self) -> float | None:
        return self.space_available / MEGA if self.space_available is not None else None

    def item_name(self) -> str:
        return f"{self.svm_name}:{self.name}"

    def incomplete(self) -> bool:
        return (
            self.space_total is None
            or self.files_maximum is None
            or self.space_available is None
            or self.files_used is None
            or self.logical_enforcement is None
            or self.logical_used is None
        )


class VolumeCountersModel(BaseModel):
    # node_name:svm_name:volume_name:volume_uuid
    # "mcc_darz_a-01:FlexPodXCS_NFS_Frank:Test_300T:00b3e6b1-5781-11ee-b0c8-00a098c54c0b"
    id: str

    fcp_write_data: int
    fcp_read_latency: int | float  # also float because computed in plugins
    iscsi_write_latency: int | float  # also float because computed in plugins
    read_latency: int | float  # also float because computed in plugins
    nfs_write_ops: int
    fcp_read_ops: int
    fcp_read_data: int
    cifs_write_ops: int
    iscsi_read_latency: int | float  # also float because computed in plugins
    nfs_write_latency: int | float  # also float because computed in plugins
    iscsi_read_ops: int
    total_read_ops: int
    cifs_read_latency: int | float  # also float because computed in plugins
    nfs_read_latency: int | float  # also float because computed in plugins
    iscsi_read_data: int
    bytes_written: int
    cifs_write_data: int
    iscsi_write_data: int
    iscsi_write_ops: int
    fcp_write_latency: int | float  # also float because computed in plugins
    fcp_write_ops: int
    nfs_read_ops: int
    bytes_read: int
    cifs_read_ops: int
    write_latency: int | float  # also float because computed in plugins
    cifs_read_data: int
    nfs_read_data: int
    total_write_ops: int
    nfs_write_data: int
    cifs_write_latency: int | float  # also float because computed in plugins

    def item_name(self) -> str:
        # compute key removing first part of id
        return self.id[self.id.find(":") + 1 :]


class DiskModel(BaseModel):
    """
    api: /api/storage/disks
    doc: https://docs.netapp.com/us-en/ontap-restmap-9131//storage-disk.html#storage-disk-get-iter

    ============
    OLD -> NEW:
    ============
    "disk-uid" -> uid
    "disk-inventory-info.shelf-bay": "bay" -> bay
    "disk-inventory-info.serial-number": "serial-number" -> serial_number
    "disk-inventory-info.vendor": "vendor-id" -> vendor

    "disk-raid-info.container-type": "raid-state" -> container_type
    "disk-raid-info.position": "raid-type"  -> NA # ! not present in new api
    "disk-raid-info.used-blocks": "used-space" -> usable_size
    "disk-raid-info.physical-blocks": "physical-space"  -> NA # ! not present in new api
    ============

    """

    uid: str
    serial_number: str
    model: str
    vendor: str
    container_type: str
    bay: int | None = None


class LunModel(BaseModel):
    """
    api: /api/storage/luns
    doc: https://docs.netapp.com/us-en/ontap-restmap-9131//lun.html#lun-copy-get-iter

    ============
    OLD -> NEW:
    ============
    "path" -> name
    "size" -> space.size
    "size-used" -> space.used
    "online" -> enabled
    "read-only" -> status.read_only
    "vserver" -> svm.name
    "volume" -> location.volume.name
    ============
    """

    name: str
    space_size: int
    space_used: int
    enabled: bool
    read_only: bool
    svm_name: str
    volume_name: str

    def size(self) -> float:
        return self.space_size / MEGA

    def free_space(self) -> float:
        return (self.space_size - self.space_used) / MEGA

    def item_name(self) -> str:
        return self.name.rsplit("/", 1)[-1]
