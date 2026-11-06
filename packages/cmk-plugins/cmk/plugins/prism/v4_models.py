#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Entities of the Nutanix v4 API, reduced to the fields the checks read

The v4 agent writes them to the prism_*_v2 sections, the parse functions read them back.
"""

from collections.abc import Sequence
from contextlib import suppress
from typing import Annotated, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    RootModel,
    StrictInt,
    ValidationError,
)


class V4Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    def to_section(self) -> dict[str, object]:
        return self.model_dump(mode="json", by_alias=True, exclude_none=True)


class HostHypervisor(V4Model):
    number_of_vms: int | None = Field(None, alias="numberOfVms")
    acropolis_connection_state: str | None = Field(None, alias="acropolisConnectionState")


class Host(V4Model):
    host_name: str = Field(alias="hostName")
    node_status: str | None = Field(None, alias="nodeStatus")
    memory_size_bytes: int | None = Field(None, alias="memorySizeBytes")
    boot_time_usecs: int | None = Field(None, alias="bootTimeUsecs")
    hypervisor: HostHypervisor = HostHypervisor()


class Hosts(RootModel[list[Host]]):
    model_config = ConfigDict(frozen=True)


class AlertParameterValue(V4Model):
    string_value: str | None = Field(None, alias="stringValue")
    int_value: int | None = Field(None, alias="intValue")

    def as_text(self) -> str | None:
        if self.string_value is not None:
            return self.string_value
        return None if self.int_value is None else str(self.int_value)


class AlertParameter(V4Model):
    param_name: str | None = Field(None, alias="paramName")
    param_value: AlertParameterValue = Field(AlertParameterValue(), alias="paramValue")


class AlertSource(V4Model):
    type: str | None = None


class Alert(V4Model):
    severity: str
    message: str
    creation_time: AwareDatetime = Field(alias="creationTime")
    parameters: list[AlertParameter] = []
    source_entity: AlertSource | None = Field(None, alias="sourceEntity")


class Alerts(RootModel[list[Alert]]):
    model_config = ConfigDict(frozen=True)


class StorageContainer(V4Model):
    """An item of the storage container list"""

    container_ext_id: str = Field(alias="containerExtId")
    name: str
    cluster_ext_id: str = Field(alias="clusterExtId")
    cache_deduplication: str | None = Field(None, alias="cacheDeduplication")


class Sample(V4Model):
    value: StrictInt
    timestamp: str


def _complete_samples(series: object) -> list[Sample]:
    """The API marks neither the value nor the timestamp as required"""
    samples: list[Sample] = []
    for sample in series if isinstance(series, list) else []:
        with suppress(ValidationError):
            samples.append(Sample.model_validate(sample))
    return samples


type Samples = Annotated[list[Sample], BeforeValidator(_complete_samples)]


def newest(samples: Sequence[Sample]) -> int | None:
    return max(samples, key=lambda sample: sample.timestamp).value if samples else None


class StorageContainerStats(V4Model):
    """The stats of one storage container, as time series

    The stats endpoint ignores $select, the model picks the fields itself.
    """

    storage_capacity_bytes: Samples = Field(
        default_factory=list,
        alias="storageCapacityBytes",
    )
    storage_free_bytes: Samples = Field(
        default_factory=list,
        alias="storageFreeBytes",
    )
    storage_replication_factor: Samples = Field(
        default_factory=list,
        alias="storageReplicationFactor",
    )
    data_reduction_dedup_saving_ratio_ppm: Samples = Field(
        default_factory=list,
        alias="dataReductionDedupSavingRatioPpm",
    )

    @property
    def has_usage(self) -> bool:
        """The check can't compute the usage without these, nor with a replication factor
        below 1"""
        replication_factor = max(
            self.storage_replication_factor, key=lambda sample: sample.timestamp, default=None
        )
        return bool(
            self.storage_capacity_bytes
            and self.storage_free_bytes
            and replication_factor is not None
            and replication_factor.value >= 1
        )


class StorageContainerWithStats(V4Model):
    name: str
    cache_deduplication: str | None = Field(None, alias="cacheDeduplication")
    stats: StorageContainerStats


class StorageContainersWithStats(RootModel[list[StorageContainerWithStats]]):
    model_config = ConfigDict(frozen=True)


class RemoteSupportConfig(V4Model):
    is_remote_support_enabled: bool = Field(alias="isRemoteSupportEnabled")


class ClusterRemoteSupport(V4Model):
    """An item of the cluster list, reduced to its remote support state"""

    config: RemoteSupportConfig


class Reference(V4Model):
    ext_id: str = Field(alias="extId")


class GuestTools(V4Model):
    version: str | None = None
    is_installed: bool | None = Field(None, alias="isInstalled")
    is_enabled: bool | None = Field(None, alias="isEnabled")


class Vm(V4Model):
    """An item of the AHV or the ESXi VM list"""

    ext_id: str = Field(alias="extId")
    name: str
    power_state: str = Field(alias="powerState")
    description: str | None = None
    memory_size_bytes: int = Field(alias="memorySizeBytes")
    # A VM that is off runs on no host
    host: Reference | None = None
    cluster: Reference
    # AHV only
    num_sockets: int | None = Field(None, alias="numSockets")
    num_cores_per_socket: int | None = Field(None, alias="numCoresPerSocket")
    protection_type: str | None = Field(None, alias="protectionType")
    guest_tools: GuestTools | None = Field(None, alias="guestTools")
    # ESXi only
    num_cpus: int | None = Field(None, alias="numCpus")
    nutanix_guest_tools: GuestTools | None = Field(None, alias="nutanixGuestTools")

    @property
    def num_vcpus(self) -> int | None:
        if self.num_cpus is not None:
            return self.num_cpus
        if self.num_sockets is None or self.num_cores_per_socket is None:
            return None
        return self.num_sockets * self.num_cores_per_socket


class VmWithHostName(V4Model):
    ext_id: str = Field(alias="extId")
    name: str
    power_state: str = Field(alias="powerState")
    description: str | None = None
    memory_size_bytes: int = Field(alias="memorySizeBytes")
    host_name: str | None = Field(None, alias="hostName")


class VmsWithHostNames(RootModel[list[VmWithHostName]]):
    model_config = ConfigDict(frozen=True)


class NodeConfig(V4Model):
    number_of_cpu_sockets: int | None = Field(None, alias="numberOfCpuSockets")
    number_of_cpu_cores: int | None = Field(None, alias="numberOfCpuCores")
    number_of_cpu_threads: int | None = Field(None, alias="numberOfCpuThreads")
    memory_size_bytes: int | None = Field(None, alias="memorySizeBytes")


class HostCluster(V4Model):
    uuid: str


class ListedHost(NodeConfig):
    """An item of the host list"""

    ext_id: str = Field(alias="extId")
    host_name: str | None = Field(None, alias="hostName")
    cluster: HostCluster | None = None


class HostStats(V4Model):
    """The stats of one host, as time series"""

    controller_avg_io_latency_usecs: Samples = Field(
        default_factory=list, alias="controllerAvgIoLatencyUsecs"
    )
    controller_avg_read_io_latency_usecs: Samples = Field(
        default_factory=list, alias="controllerAvgReadIoLatencyUsecs"
    )
    controller_avg_write_io_latency_usecs: Samples = Field(
        default_factory=list, alias="controllerAvgWriteIoLatencyUsecs"
    )
    controller_read_io_bandwidth_kbps: Samples = Field(
        default_factory=list, alias="controllerReadIoBandwidthKbps"
    )
    controller_write_io_bandwidth_kbps: Samples = Field(
        default_factory=list, alias="controllerWriteIoBandwidthKbps"
    )
    controller_num_read_iops: Samples = Field(default_factory=list, alias="controllerNumReadIops")
    controller_num_write_iops: Samples = Field(default_factory=list, alias="controllerNumWriteIops")
    hypervisor_cpu_usage_ppm: Samples = Field(default_factory=list, alias="hypervisorCpuUsagePpm")
    cpu_capacity_hz: Samples = Field(default_factory=list, alias="cpuCapacityHz")
    aggregate_hypervisor_memory_usage_ppm: Samples = Field(
        default_factory=list, alias="aggregateHypervisorMemoryUsagePpm"
    )
    storage_capacity_bytes: Samples = Field(default_factory=list, alias="storageCapacityBytes")
    free_physical_storage_bytes: Samples = Field(
        default_factory=list, alias="freePhysicalStorageBytes"
    )


class DiskAdvanceConfig(V4Model):
    is_unhealthy: bool | None = Field(None, alias="isUnhealthy")
    is_mounted: bool | None = Field(None, alias="isMounted")


class DiskConfig(V4Model):
    location: int | None = None
    model: str | None = None
    serial_number: str | None = Field(None, alias="serialNumber")
    storage_tier: str | None = Field(None, alias="storageTier")
    disk_advance_config: DiskAdvanceConfig = Field(DiskAdvanceConfig(), alias="diskAdvanceConfig")


class ListedDisk(DiskConfig):
    """An item of the disk list"""

    ext_id: str = Field(alias="extId")
    node_ext_id: str | None = Field(None, alias="nodeExtId")
    storage_pool_ext_id: str | None = Field(None, alias="storagePoolExtId")
    cluster_ext_id: str | None = Field(None, alias="clusterExtId")


class DiskStats(V4Model):
    """The stats of one disk, as time series

    The stats endpoint ignores $select, the model picks the fields itself.
    """

    disk_capacity_bytes: Samples = Field(default_factory=list, alias="diskCapacityBytes")
    disk_free_bytes: Samples = Field(default_factory=list, alias="diskFreeBytes")


class NodeDisk(V4Model):
    config: DiskConfig
    stats: DiskStats = DiskStats()


class Node(V4Model):
    """A host with its stats and disks, as written to prism_host_v2"""

    config: NodeConfig
    stats: HostStats
    disks: list[NodeDisk] = []


class VmStatsSample(V4Model):
    timestamp: str
    controller_avg_io_latency_micros: StrictInt | None = Field(
        None, alias="controllerAvgIoLatencyMicros"
    )
    controller_avg_read_io_latency_micros: StrictInt | None = Field(
        None, alias="controllerAvgReadIoLatencyMicros"
    )
    controller_avg_write_io_latency_micros: StrictInt | None = Field(
        None, alias="controllerAvgWriteIoLatencyMicros"
    )
    controller_avg_read_io_size_kb: StrictInt | None = Field(
        None, alias="controllerAvgReadIoSizeKb"
    )
    controller_avg_write_io_size_kb: StrictInt | None = Field(
        None, alias="controllerAvgWriteIoSizeKb"
    )
    hypervisor_cpu_usage_ppm: StrictInt | None = Field(None, alias="hypervisorCpuUsagePpm")
    hypervisor_cpu_ready_time_ppm: StrictInt | None = Field(None, alias="hypervisorCpuReadyTimePpm")
    guest_memory_usage_ppm: StrictInt | None = Field(None, alias="guestMemoryUsagePpm")


def _valid_vm_samples(series: object) -> list[VmStatsSample]:
    samples: list[VmStatsSample] = []
    for sample in series if isinstance(series, list) else []:
        with suppress(ValidationError):
            samples.append(VmStatsSample.model_validate(sample))
    return samples


type VmStatsSamples = Annotated[list[VmStatsSample], BeforeValidator(_valid_vm_samples)]


class VmDetails(V4Model):
    """One VM with its config and stats, for the piggyback host of the VM"""

    ext_id: str = Field(alias="extId")
    name: str
    hypervisor: Literal["AHV", "ESXI"]
    power_state: str = Field(alias="powerState")
    host_name: str | None = Field(None, alias="hostName")
    num_vcpus: int | None = Field(None, alias="numVcpus")
    memory_size_bytes: int = Field(alias="memorySizeBytes")
    protection_type: str | None = Field(None, alias="protectionType")
    guest_tools: GuestTools | None = Field(None, alias="guestTools")
    # None: Prism Central couldn't list the stats
    stats: VmStatsSamples | None = None


class HostNic(V4Model):
    """A physical NIC of a host, as written to prism_host_networks_v2"""

    name: str | None = None
    mac_address: str | None = Field(None, alias="macAddress")
    link_speed_in_kbps: int | None = Field(None, alias="linkSpeedInKbps")
    # "1": up
    interface_status: str | None = Field(None, alias="interfaceStatus")


class ListedHostNic(HostNic):
    """An item of the host NIC list"""

    node_uuid: str | None = Field(None, alias="nodeUuid")


class HostNics(RootModel[list[HostNic]]):
    model_config = ConfigDict(frozen=True)
