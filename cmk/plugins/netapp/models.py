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
from typing import Any

from pydantic import BaseModel

MEGA = 1024.0 * 1024.0


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
    "disk-raid-info.physical-blocks": "physical-space"  -> see below
    bytes-per-sector → bytes_per_sector
    capacity-sectors → sector_count
    ============

    """

    uid: str
    serial_number: str
    model: str
    vendor: str
    container_type: str
    bay: int | None = None

    bytes_per_sector: int
    sector_count: int

    def space(self) -> int:
        return self.bytes_per_sector * self.sector_count


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


class AggregateSpace(BaseModel):
    class BlockStorage(BaseModel):
        # default None inherited from old NetApp API logic
        available: int | None = None
        size: int | None = None

    block_storage: BlockStorage


class AggregateModel(BaseModel):
    """
    api: /api/storage/aggregates
    doc: https://docs.netapp.com/us-en/ontap-restmap-9131//aggr.html#aggr-get-iter

    ============
    OLD -> NEW:
    ============
    "aggregate-name" -> name
    "aggr-space-attributes.size-available": "size-available" -> space.block_storage.available
    "aggr-space-attributes.size-total": "size-total" -> space.block_storage.size
    ============
    """

    name: str
    space: AggregateSpace

    def size_total(self) -> float | None:
        return (
            self.space.block_storage.size / MEGA
            if self.space.block_storage.size is not None
            else None
        )

    def size_avail(self) -> float | None:
        return (
            self.space.block_storage.available / MEGA
            if self.space.block_storage.available is not None
            else None
        )


class SvmModel(BaseModel):
    """
    api: /api/svm/svms
    docs: https://docs.netapp.com/us-en/ontap-restmap-9121//vserver.html#vserver-get-iter
    Section was: netapp_api_vs_status - vserver

    ============
    OLD -> NEW:
    ============
    "vserver-name" -> name
    "state" -> state
    "vserver-subtype" -> subtype
    ============

    Wraps information coming from /svm/svms
    see https://library.netapp.com/ecmdocs/ECMLP2885799/html/index.html#/svm/svm_collection_get
    """

    name: str
    # default None inherited from old NetApp API logic
    state: str | None = None
    subtype: str | None = None


class IpInterfaceModel(BaseModel):
    """Wraps information coming from "/api/network/ip/interfaces", see
    - https://library.netapp.com/ecmdocs/ECMLP2885799/html/index.html#/networking/network_ip_interfaces_get
    - https://docs.netapp.com/us-en/ontap-restmap-9131//net.html?q=net-interface-get-iter#net-interface-get-iter


    ============
    OLD -> NEW:
    ============
    "interface-name" -> name
    "link-status" -> state
    "failover_ports" -> Moved to failover in port model
    "operational-speed" -> speed
    "mac-address" -> mac_address
    ============

    """

    name: str
    uuid: str
    state: str | None = None  # default None inherited from old NetApp API logic
    enabled: bool
    node_name: str
    port_name: str
    failover: str
    home_node: str
    home_port: str
    is_home: bool

    def serialize(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "uuid": self.uuid,
            "state": self.state,
            "enabled": self.enabled,
            "node_name": self.node_name,
            "port_name": self.port_name,
            "failover": self.failover,
            "home-node": self.home_node,
            "home-port": self.home_port,
            "is-home": self.is_home,
        }


class PortModel(BaseModel):
    """
    api: /api/network/ethernet/ports
    doc: https://docs.netapp.com/us-en/ontap-restmap-9131//net.html#net-port-get

    ============
    OLD -> NEW:
    ============
    "node" -> node
    "port" -> name
    "operational-speed" -> speed
    "health-status" -> NOT AVAILABLE IN REST API

    "operational-status" -> state
    "mac-address" -> mac_address
    ============

    """

    uuid: str
    name: str
    node_name: str
    state: str
    speed: int | None = None
    port_type: str
    mac_address: str | None = None
    broadcast_domain: str | None = None

    def item_name(self) -> str:
        return f"{self.port_type.capitalize()} port {self.node_name}.{self.name}"

    def serialize(self) -> dict[str, Any]:
        return {
            "port-uuid": self.uuid,
            "port-name": self.name,
            "port-node": self.node_name,
            "port_state": self.state,
            "speed": self.speed,
            "port_type": self.port_type,
            "mac-address": self.mac_address,
            "broadcast_domain": self.broadcast_domain,
        }


class InterfaceCounters(BaseModel):
    """
    "recv_data" -> received_data
    "send_data" -> sent_data
    "recv_mcasts" -> ! NA
    "send_mcasts" -> ! NA
    "recv_errors" -> received_errors
    "send_errors" -> sent_errors
    "recv_packet" -> received_packets
    "send_packet" -> sent_packets
    """

    # id composition: node_name:interface_name:??
    id: str

    recv_data: int
    recv_packet: int
    recv_errors: int
    send_data: int
    send_packet: int
    send_errors: int


class Version(BaseModel):
    """Stores the NetApp ONTAP release version information"""

    full: str
    generation: int
    major: int
    minor: int


class NodeModel(BaseModel):
    """
    Wraps information coming from /api/cluster/nodes/{node_uuid}
    see https://library.netapp.com/ecmdocs/ECMLP2885799/html/index.html#/cluster/node_get

    api: /api/cluster/nodes
    doc: https://docs.netapp.com/us-en/ontap-restmap-9131//system.html#system-get-node-info-iter


    STATUS PLUGIN:
    ============
    OLD -> NEW:
    ============
    "node" -> name
    "cpu-busytime": "cpu_busy" -> # ! NO REST equivalent
    "nvram-battery-status" -> nvram.battery_state
    "number-of-processors": "num_processors" -> controller.cpu.count
    ============
    config_scale={"cpu-busytime": 1000000},

    INFO PLUGIN:
    doc: https://docs.netapp.com/us-en/ontap-restmap-9131//system.html#system-cache-mirror-get-iter

    ============
    OLD -> NEW:
    ============

    backplane-serial-number -> NA # ! TODO: NA
    system-model -> model
    system-machine-type -> system_machine_type
    system-serial-number -> serial_number
    system-id -> system_id
    vendor-id -> NA # ! TODO: NA
    cpu-processor-type -> controller.cpu.processor
    ============

    """

    name: str
    uuid: str
    version: Version
    cpu_count: int | None = None  # default None inherited from old NetApp API logic
    battery_state: str

    model: str
    system_machine_type: str | None = None
    serial_number: str
    system_id: str
    cpu_processor: str | None = None  # default None inherited from old NetApp API logic


class ShelfFanModel(BaseModel):
    """

    api: /api/storage/shelves
    doc: https://docs.netapp.com/us-en/ontap-restmap-9131//ses.html#storage-shelf-environment-list-info


    ============
    OLD -> NEW:
    ============
    cooling-element-number -> fans.id
    cooling-element-is-not-installed -> fans.installed  # comment: fans.installed is the inverse of cooling-element-is-not-installed in REST !! NOT WORKING, waiting for discord answer
    cooling-element-is-error -> fans.state  # comment: cooling-element-is-error is simplified to "ok" and "error" in REST
    rpm -> fans.rpm
    ============
    """

    list_id: str  # shelf id
    id: int
    state: str  # "ok" or "error"
    rpm: int
    installed: bool | None = None  # TODO remove non when query fixed

    def item_name(self) -> str:
        return f"{self.list_id}/{self.id}"


class ShelfTemperatureModel(BaseModel):
    """

    api: /api/storage/shelves
    doc: https://docs.netapp.com/us-en/ontap-restmap-9131//ses.html#storage-shelf-environment-list-info


    ============
    OLD -> NEW:
    ============
    temp-sensor-element-no → temperature_sensors.id
    temp-sensor-is-not-installed → temperature_sensors.installed comment: temperature_sensors.installed is the inverse of temp-sensor-is-not-installed in REST
    temp-sensor-is-error → temperature_sensors.state comment: temp-sensor-is-error is simplified to "ok" and "error" in REST

    temp-sensor-current-temperature → temperature_sensors.temperature
    temp-sensor-is-ambient → temperature_sensors.ambient
    temp-sensor-current-condition → NA
    temp-sensor-low-warning → temperature_sensors.threshold.low.warning
    temp-sensor-low-critical → temperature_sensors.threshold.low.critical
    temp-sensor-hi-warning → temperature_sensors.threshold.high.warning
    temp-sensor-hi-critical → temperature_sensors.threshold.high.critical
    ============
    """

    list_id: str  # shelf id
    id: int
    installed: bool | None = None  # TODO remove non when query fixed
    state: str  # "ok" or "error"

    temperature: int
    ambient: bool

    low_warning: int | None = None
    low_critical: int | None = None
    high_warning: int | None = None
    high_critical: int | None = None

    def item_name(self) -> str:
        return f"{self.list_id}/{self.id}"
