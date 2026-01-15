#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="mutable-override"

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"


"""Wrapper from marshmallow based NetApp-Python-Library pydantic Checkmk-NetApp-Protocol
There is no real logic in here, just filtering, type hinting, validating, restructuring.

Docs:
- https://github.com/NetApp/ontap-rest-python
- https://library.netapp.com/ecmdocs/ECMLP2885799/html/index.html#/
- https://library.netapp.com/ecmdocs/ECMLP2885777/html/resources/counter_table.html
- https://docs.netapp.com/us-en/ontap-restmap-9131//perf.html#perf-object-instance-list-info-iter
"""

import datetime
from collections.abc import Sequence
from typing import Any, Literal

from pydantic import BaseModel, Field

MEGA = 1024.0 * 1024.0


class VolumeModel(BaseModel):
    """
    api: /api/storage/volumes
    doc: https://docs.netapp.com/us-en/ontap-restmap-9131//volume.html#volume-footprint-get-iter
    call: next(NetAppResource.Volume.get_collection(fields="*"))

    Volume plugin:
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

    Snapshot plugin:
    ============
    OLD -> NEW:
    ============
    "name" -> the volume name (see above)
    "state" -> the volume state (see above)
    "snapshot-percent-reserved" -> space.snapshot.reserve_percent
    "snapshot-blocks-reserved" -> space.snapshot.reserve_size
    "reserve-used-actual" -> space.snapshot.used
    ============


    """

    uuid: str
    state: str | None = None
    name: str
    msid: int
    svm_name: str
    svm_uuid: str

    # None because sometime this data is not present:
    space_available: int | None = None
    space_total: int | None = None
    logical_enforcement: bool | None = None
    logical_used: int | None = None
    files_maximum: int | None = None
    files_used: int | None = None
    snapshot_reserve_size: int | None = None
    snapshot_used: int | None = None
    snapshot_reserve_percent: int | None = None

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
    serial_number: str | None = None
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
    space_used: int | None = None
    enabled: bool
    read_only: bool | None = None
    svm_name: str
    volume_name: str

    def size(self) -> float:
        return self.space_size / MEGA

    def free_space(self) -> float:
        if self.space_used is None:
            raise ValueError("space_used must be available to calculate free space")
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

    full: str = ""
    generation: int
    major: int
    minor: int

    def _tuple(self):
        return (self.generation, self.major, self.minor)

    # minimum set of used comparison methods
    def __lt__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return self._tuple() < other._tuple()

    def __ge__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return self._tuple() >= other._tuple()


class NodeModel(BaseModel):
    """
    Wraps information coming from /api/cluster/nodes/{node_uuid}
    see https://library.netapp.com/ecmdocs/ECMLP2885799/html/index.html#/cluster/node_get

    api: /api/cluster/nodes
    doc: https://docs.netapp.com/us-en/ontap-restapi/get-cluster-nodes-.html#definitions

    STATUS PLUGIN:
    ============
    OLD -> NEW:
    ============
    "node" -> name
    "cpu-busytime": "cpu_busy" -> metric.processor_utilization
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

    processor_utilization: float
    processor_utilization_timestamp: datetime.datetime  # provided in ISO 8601 format
    date: datetime.datetime | None = None


class ShelfObjectModel(BaseModel):
    list_id: str  # shelf id
    id: int
    state: str  # "ok" or "error"
    installed: bool | None = None  # subclasses have this field in different versions each

    def item_name(self) -> str:
        return f"{self.list_id}/{self.id}"

    def consider_installed(self) -> bool:
        # safe approach
        return self.installed is None or self.installed


class ShelfFanModel(ShelfObjectModel):
    """

    api: /api/storage/shelves
    doc: https://docs.netapp.com/us-en/ontap-restmap-9131//ses.html#storage-shelf-environment-list-info


    ============
    OLD -> NEW:
    ============
    cooling-element-number -> fans.id
    cooling-element-is-not-installed -> fans.installed  # available from  Netapp version 9.13.1
    cooling-element-is-error -> fans.state  # comment: cooling-element-is-error is simplified to "ok" and "error" in REST
    rpm -> fans.rpm
    ============
    """


class ShelfTemperatureModel(ShelfObjectModel):
    """

    api: /api/storage/shelves
    doc: https://docs.netapp.com/us-en/ontap-restmap-9131//ses.html#storage-shelf-environment-list-info


    ============
    OLD -> NEW:
    ============
    temp-sensor-element-no → temperature_sensors.id
    temp-sensor-is-not-installed → temperature_sensors.installed # available from  Netapp version 9.13.1
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

    temperature: int | None
    state: Literal["ok", "error"]
    ambient: bool

    low_warning: int | None = None
    low_critical: int | None = None
    high_warning: int | None = None
    high_critical: int | None = None


class ShelfPsuModel(ShelfObjectModel):
    """

    api: /api/storage/shelves
    doc: https://docs.netapp.com/us-en/ontap-restmap-9131//ses.html#storage-shelf-environment-list-info


    ============
    OLD -> NEW:
    ============
    power-supply-element-no → frus.id
    power-supply-is-not-installed → frus.installed  # available from  Netapp version 9.11.1
    power-supply-is-error → frus.state
    ============
    """


class AlertModel(BaseModel):
    """
    https://docs.netapp.com/us-en/ontap-restmap-9141//diagnosis.html#diagnosis-alert-get
    """

    name: str
    # this fields should always be present since ONTAP v 9.8 but better be safe than sorry...
    acknowledge: bool = False
    acknowledger: str = ""
    suppress: bool = False
    suppressor: str = ""


class SvmTrafficCountersModel(BaseModel):
    """
    cfr: https://docs.netapp.com/us-en/ontap-pcmap-9141/
    """

    svm_name: str
    table: str
    counters: Sequence[dict]


SensorState = Literal[
    "bad",
    "crit_high",
    "crit_low",
    "disabled",
    "failed",
    "fault",
    "ignored",
    "init_failed",
    "invalid",
    "normal",
    "not_available",
    "not_present",
    "retry",
    "uninitialized",
    "unknown",
    "warn_high",
    "warn_low",
]


class EnvironmentSensorModel(BaseModel):
    """
    GET /api/cluster/sensors
    cfr: https://docs.netapp.com/us-en/ontap-restmap-9131//environment.html
    was: environment-sensors-get-iter

    """

    name: str
    node_name: str


class EnvironmentThresholdSensorModel(EnvironmentSensorModel):
    sensor_type: Literal["thermal", "fan", "voltage", "current"]
    value: int | None = None
    warning_high_threshold: int | None = None
    warning_low_threshold: int | None = None
    critical_high_threshold: int | None = None
    critical_low_threshold: int | None = None
    threshold_state: SensorState
    value_units: str | None = None


class EnvironmentDiscreteSensorModel(EnvironmentSensorModel):
    sensor_type: Literal["discrete"]
    discrete_value: str | None = None
    discrete_state: SensorState


class DiscrimnatorEnvSensorModel(BaseModel):
    sensor: EnvironmentThresholdSensorModel | EnvironmentDiscreteSensorModel = Field(
        discriminator="sensor_type"
    )


class QtreeQuotaModel(BaseModel):
    """

    api: GET /api/storage/quota/reports
    doc: https://docs.netapp.com/us-en/ontap-restmap-9131//quota.html#quota-report-iter


    ============
    OLD -> NEW:
    ============
    "tree" -> name
    "volume" -> volume.name
    "disk-limit" -> space.hard_limit
    "disk-used" -> space.used.total
    "quota-type" -> type # NA
    "quota-users.quota-user.quota-user-name" -> users
    ============
    """

    name: str | None = None
    volume: str
    hard_limit: int | None = None
    used_total: int | None = None
    users: Sequence[str]


class SnapMirrorModel(BaseModel):
    """
    doc: https://docs.netapp.com/us-en/ontap-restmap-98/snapmirror.html#snapmirror-get

    destination-volume -> NA
    destination-volume-node -> NA

    policy -> policy.type, policy.name
    "mirror-state" -> state
    "source-vserver" -> source.svm.name, source.svm.uuid
    "lag-time" -> lag_time
    "relationship-status" -> state
    "destination-location" ->  destination.path
    """

    destination_svm: str
    policy_name: str | None = None
    policy_type: str | None = None
    state: str | None = None
    transfer_state: (
        Literal["aborted", "failed", "hard_aborted", "queued", "success", "transferring"] | None
    ) = None
    source_svm_name: str | None = None
    lag_time: datetime.timedelta | None = None
    destination: str

    def lagtime(self) -> float | None:
        """
        see: https://kb.netapp.com/onprem/ontap/dp/SnapMirror/What_is_SnapMirror_lag_time
        """

        if self.lag_time is None:
            return None

        return self.lag_time.total_seconds()


class FcPortModel(BaseModel):
    """
    cfr: https://docs.netapp.com/us-en/ontap-restmap-9131//fcp.html#fcp-adapter-get-iter
    """

    supported_protocols: Sequence[str]
    wwpn: str
    wwnn: str
    physical_protocol: str
    state: str
    name: str
    description: str
    enabled: bool
    node_name: str
    connected_speed: int | None = None  # gigabit per second

    def speed_in_bps(self) -> int | None:
        """Returns the speed in bits per second"""
        return self.connected_speed * 1000**3 if self.connected_speed is not None else None


class FcInterfaceTrafficCountersModel(BaseModel):
    """
    cfr: https://docs.netapp.com/us-en/ontap-pcmap-9141/
    """

    svm_name: str
    table: str
    counters: Sequence[dict]
    name: str  # was: instance-name
    port_wwpn: str
