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
from collections.abc import Iterator, Sequence

from netapp_ontap import resources as NetAppResource
from netapp_ontap.host_connection import HostConnection
from pydantic import BaseModel


class LogicalSpaceAttributes(BaseModel):
    enforcement: bool
    used: int


class SpaceAttributes(BaseModel):
    available: int
    afs_total: int
    logical_space: LogicalSpaceAttributes


class SvmAttributes(BaseModel):
    name: str
    uuid: str


class FilesAttributes(BaseModel):
    maximum: int
    used: int


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
    "volume-id-attributes.node" -> NA  # ! HELP missing?
    "volume-id-attributes.msid" -> msid

    "volume-inode-attributes.files-total" -> files.maximum
    "volume-inode-attributes.files-used" -> files.used
    ============

    FIXME:
    - Can I ignore the NA fields? - check during plugin migration

    """

    uuid: str
    state: str | None = None
    name: str
    msid: int
    space: SpaceAttributes | None = None
    svm: SvmAttributes
    files: FilesAttributes | None = None


def get_volumes(connection: HostConnection) -> Iterator[VolumeModel]:
    field_query = {
        "uuid",
        "state",
        "name",
        "msid",
        "space.available",
        "space.afs_total",
        "space.logical_space.enforcement",
        "space.logical_space.used",
        "svm.name",
        "svm.uuid",
        "files.maximum",
        "files.used",
    }

    yield from (
        VolumeModel.model_validate(element.to_dict())
        for element in NetAppResource.Volume.get_collection(
            connection=connection, fields=",".join(field_query)
        )
    )


class VolumeCounter(BaseModel):
    name: str
    value: int


class VolumeCountersRowModel(BaseModel):
    id: str
    counters: Sequence[VolumeCounter]


volumes_counters_field_query = {
    "fcp.write_data",
    "fcp.read_latency",
    "iscsi.write_latency",
    "read_latency",
    "nfs.write_ops",
    "fcp.read_ops",
    "fcp.read_data",
    "cifs.write_ops",
    "iscsi.read_latency",
    "nfs.write_latency",
    "iscsi.read_ops",
    "total_read_ops",
    "cifs.read_latency",
    "nfs.read_latency",
    "iscsi.read_data",
    "bytes_written",
    "cifs.write_data",
    "iscsi.write_data",
    "iscsi.write_ops",
    "fcp.write_latency",
    "fcp.write_ops",
    "nfs.read_ops",
    "bytes_read",
    "cifs.read_ops",
    "write_latency",
    "cifs.read_data",
    "nfs.read_data",
    "total_write_ops",
    "nfs.write_data",
    "cifs.write_latency",
}


def get_volume_counters(
    connection: HostConnection, volume_id: str
) -> Iterator[VolumeCountersRowModel]:
    # fcp_write_data -> fcp.write_data
    # fcp_read_latency -> fcp.read_latency
    # iscsi_write_latency -> iscsi.write_latency
    # read_latency -> read_latency
    # nfs_write_ops -> nfs.write_ops
    # fcp_read_ops -> fcp.read_ops
    # fcp_read_data -> fcp.read_data
    # cifs_write_ops -> cifs.write_ops
    # iscsi_read_latency -> iscsi.read_latency
    # nfs_write_latency -> nfs.write_latency
    # iscsi_read_ops -> iscsi.read_ops
    # read_ops -> total_read_ops
    # cifs_read_latency -> cifs.read_latency
    # nfs_read_latency -> nfs.read_latency
    # iscsi_read_data -> iscsi.read_data
    # san_read_ops  # ! missing
    # san_read_data # ! missing
    # san_read_latency # ! missing
    # write_data -> bytes_written
    # cifs_write_data -> cifs.write_data
    # iscsi_write_data -> iscsi.write_data
    # san_write_latency # ! missing
    # san_write_data # ! missing
    # iscsi_write_ops -> iscsi.write_ops
    # san_write_ops # ! missing
    # fcp_write_latency -> fcp.write_latency
    # fcp_write_ops -> fcp.write_ops
    # nfs_read_ops -> nfs.read_ops
    # read_data -> bytes_read
    # cifs_read_ops -> cifs.read_ops
    # write_latency -> write_latency
    # cifs_read_data -> cifs.read_data
    # nfs_read_data -> nfs.read_data
    # write_ops -> total_write_ops
    # nfs_write_data -> nfs.write_data
    # cifs_write_latency -> cifs.write_latency

    yield from (
        VolumeCountersRowModel.model_validate(element.to_dict())
        for element in NetAppResource.CounterRow.get_collection(
            "volume",
            id=volume_id,
            connection=connection,
            fields="counters",
            max_records=None,  # type: ignore # pylint disable=arg-type not working
            **{"counters.name": "|".join(volumes_counters_field_query)},
        )
    )


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
    "disk-raid-info.position": "raid-type"  -> NA # ! HELP
    "disk-raid-info.used-blocks": "used-space" -> usable_size
    "disk-raid-info.physical-blocks": "physical-space"  -> NA # ! HELP
    ============

    TODO:
    - The old code uses config scales (see: cmk/special_agents/agent_netapp.py:945)
        Implement it here!
    - Can I ignore the NA fields? See the plugin

    """

    uid: str
    serial_number: str
    model: str
    vendor: str
    container_type: str
    usable_size: int | None = None


def get_disks(connection: HostConnection) -> Iterator[DiskModel]:
    field_query = {
        "uid",
        "serial_number",
        "model",
        "vendor",
        "container_type",
        "usable_size",
    }
    yield from (
        DiskModel.model_validate(element.to_dict())
        for element in NetAppResource.Disk.get_collection(
            connection=connection, fields=",".join(field_query)
        )
    )
