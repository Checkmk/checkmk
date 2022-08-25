#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping, MutableMapping, NamedTuple, Sequence

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)

from .agent_based_api.v1 import get_value_store, register, render, Result, Service, State
from .utils.df import df_check_filesystem_single, FILESYSTEM_DEFAULT_PARAMS
from .utils.scaleio import (
    convert_scaleio_space_into_mb,
    convert_to_bytes,
    KNOWN_CONVERSION_VALUES_INTO_MB,
    parse_scaleio,
)

# <<<scaleio_storage_pool>>>
# STORAGE_POOL 59c7748300000000:
#        ID                                                 59c7748300000000
#        NAME                                               pool01
#        MAX_CAPACITY_IN_KB                                 65.5 TB (67059 GB)
#        UNUSED_CAPACITY_IN_KB                              17.2 TB (17635 GB)
#        FAILED_CAPACITY_IN_KB                              0 Bytes
#        TOTAL_READ_BWC                                     0 IOPS 0 Bytes per-second
#        TOTAL_WRITE_BWC                                    0 IOPS 0 Bytes per-second
#        REBALANCE_READ_BWC                                 0 IOPS 0 Bytes per-second
#        REBALANCE_WRITE_BWC                                0 IOPS 0 Bytes per-second
#


class FilesystemStoragePool(NamedTuple):
    total_capacity: float
    free_capacity: float
    failed_capacity: float


class FilesystemStorageConversionError(NamedTuple):
    unit: str


class DiskReadWrite(NamedTuple):
    read_throughput: float | None
    write_throughput: float | None
    read_operations: float
    write_operations: float


class StoragePool(NamedTuple):
    pool_id: str
    name: str
    filesystem_storage_pool: FilesystemStoragePool | FilesystemStorageConversionError
    total_io: DiskReadWrite
    rebalance_io: DiskReadWrite


ScaleioStoragePoolSection = Mapping[str, StoragePool]


def _create_disk_read_write(read_data: Sequence[str], write_data: Sequence[str]) -> DiskReadWrite:
    return DiskReadWrite(
        read_throughput=convert_to_bytes(float(read_data[2]), read_data[3]),
        write_throughput=convert_to_bytes(float(write_data[2]), write_data[3]),
        read_operations=float(read_data[0]),
        write_operations=float(write_data[0]),
    )


def _create_filesystem_storage_pool(
    unit: str,
    total_capacity: str,
    free_capacity: str,
    failed_capacity: str,
) -> FilesystemStoragePool | FilesystemStorageConversionError:

    if unit not in KNOWN_CONVERSION_VALUES_INTO_MB:
        return FilesystemStorageConversionError(unit=unit)

    return FilesystemStoragePool(
        total_capacity=convert_scaleio_space_into_mb(
            unit,
            float(total_capacity),
        ),
        free_capacity=convert_scaleio_space_into_mb(
            unit,
            float(free_capacity),
        ),
        failed_capacity=float(failed_capacity),
    )


def parse_scaleio_storage_pool(string_table: StringTable) -> ScaleioStoragePoolSection:

    section: MutableMapping[str, StoragePool] = {}
    for pool_id, pool in parse_scaleio(string_table, "STORAGE_POOL").items():
        pool_capacity = pool["MAX_CAPACITY_IN_KB"]

        section[pool_id] = StoragePool(
            pool_id=pool_id,
            name=pool["NAME"][0],
            filesystem_storage_pool=_create_filesystem_storage_pool(
                unit=pool_capacity[1],
                total_capacity=pool_capacity[0],
                free_capacity=pool["UNUSED_CAPACITY_IN_KB"][0],
                failed_capacity=pool["FAILED_CAPACITY_IN_KB"][0],
            ),
            total_io=_create_disk_read_write(
                read_data=pool["TOTAL_READ_BWC"],
                write_data=pool["TOTAL_WRITE_BWC"],
            ),
            rebalance_io=_create_disk_read_write(
                read_data=pool["REBALANCE_READ_BWC"],
                write_data=pool["REBALANCE_WRITE_BWC"],
            ),
        )
    return section


register.agent_section(
    name="scaleio_storage_pool",
    parse_function=parse_scaleio_storage_pool,
)


def discover_scaleio_storage_pool(section: ScaleioStoragePoolSection) -> DiscoveryResult:
    for pool_id in section:
        yield Service(item=pool_id)


def _check_scaleio_storage_pool(
    item: str,
    params: Mapping[str, Any],
    section: ScaleioStoragePoolSection,
    value_store: MutableMapping[str, Any],
) -> CheckResult:
    if not (storage_pool := section.get(item)):
        return

    if isinstance(storage_pool.filesystem_storage_pool, FilesystemStorageConversionError):
        yield Result(
            state=State.UNKNOWN,
            summary=f"Unknown unit: {storage_pool.filesystem_storage_pool.unit}",
        )
        return

    yield from df_check_filesystem_single(
        value_store=value_store,
        mountpoint=item,
        filesystem_size=storage_pool.filesystem_storage_pool.total_capacity,
        free_space=storage_pool.filesystem_storage_pool.free_capacity,
        reserved_space=0.0,
        inodes_avail=None,
        inodes_total=None,
        params=params,
    )

    if storage_pool.filesystem_storage_pool.failed_capacity > 0:
        yield Result(
            state=State.CRIT,
            summary=f"Failed Capacity: {render.bytes(storage_pool.filesystem_storage_pool.failed_capacity)}",
        )


def check_scaleio_storage_pool(
    item: str, params: Mapping[str, Any], section: ScaleioStoragePoolSection
) -> CheckResult:
    yield from _check_scaleio_storage_pool(item, params, section, value_store=get_value_store())


register.check_plugin(
    name="scaleio_storage_pool",
    service_name="ScaleIO SP capacity %s",
    discovery_function=discover_scaleio_storage_pool,
    check_function=check_scaleio_storage_pool,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
