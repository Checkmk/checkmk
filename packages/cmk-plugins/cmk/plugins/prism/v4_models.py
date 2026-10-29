#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Entities of the Nutanix v4 API, reduced to the fields the checks read

The v4 agent writes them to the prism_*_v2 sections, the parse functions read them back.
"""

from contextlib import suppress
from typing import Annotated

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
