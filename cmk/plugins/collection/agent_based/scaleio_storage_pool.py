#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import time
from collections.abc import Mapping, MutableMapping
from typing import Any, NamedTuple

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.df import df_check_filesystem_single, FILESYSTEM_DEFAULT_PARAMS
from cmk.plugins.lib.diskstat import check_diskstat_dict_legacy
from cmk.plugins.lib.scaleio import (
    convert_scaleio_space_into_mb,
    create_disk_read_write,
    DiskReadWrite,
    KNOWN_CONVERSION_VALUES_INTO_MB,
    parse_scaleio,
    StorageConversionError,
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


class StoragePool(NamedTuple):
    pool_id: str
    name: str
    filesystem_storage_pool: FilesystemStoragePool | StorageConversionError
    total_io: DiskReadWrite | StorageConversionError
    rebalance_io: DiskReadWrite | StorageConversionError


ScaleioStoragePoolSection = Mapping[str, StoragePool]


def _create_filesystem_storage_pool(
    unit: str,
    total_capacity: str,
    free_capacity: str,
    failed_capacity: str,
) -> FilesystemStoragePool | StorageConversionError:
    if unit not in KNOWN_CONVERSION_VALUES_INTO_MB:
        return StorageConversionError(unit=unit)

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
    section: dict[str, StoragePool] = {}
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
            total_io=create_disk_read_write(
                read_data=pool["TOTAL_READ_BWC"],
                write_data=pool["TOTAL_WRITE_BWC"],
            ),
            rebalance_io=create_disk_read_write(
                read_data=pool["REBALANCE_READ_BWC"],
                write_data=pool["REBALANCE_WRITE_BWC"],
            ),
        )
    return section


agent_section_scaleio_storage_pool = AgentSection(
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

    if isinstance(storage_pool.filesystem_storage_pool, StorageConversionError):
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


check_plugin_scaleio_storage_pool = CheckPlugin(
    name="scaleio_storage_pool",
    service_name="ScaleIO SP capacity %s",
    discovery_function=discover_scaleio_storage_pool,
    check_function=check_scaleio_storage_pool,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)


def _check_scaleio_storage_pool_disks(
    params: Mapping[str, Any],
    pool_name: str,
    disk_stats: DiskReadWrite | StorageConversionError,
    value_store: MutableMapping[str, Any],
) -> CheckResult:
    yield Result(state=State.OK, summary=f"Name: {pool_name}")

    if isinstance(disk_stats, StorageConversionError):
        yield Result(
            state=State.UNKNOWN,
            summary=f"Unknown unit: {disk_stats.unit}",
        )
        return

    yield from check_diskstat_dict_legacy(
        params=params,
        disk={
            "read_ios": disk_stats.read_operations,
            "read_throughput": disk_stats.read_throughput,
            "write_ios": disk_stats.write_operations,
            "write_throughput": disk_stats.write_throughput,
        },
        value_store=value_store,
        this_time=time.time(),
    )


def check_scaleio_storage_pool_totalrw(
    item: str,
    params: Mapping[str, Any],
    section: ScaleioStoragePoolSection,
) -> CheckResult:
    if not (pool := section.get(item)):
        return

    yield from _check_scaleio_storage_pool_disks(
        params=params,
        pool_name=pool.name,
        disk_stats=pool.total_io,
        value_store=get_value_store(),
    )


check_plugin_scaleio_storage_pool_totalrw = CheckPlugin(
    name="scaleio_storage_pool_totalrw",
    service_name="ScaleIO SP total IO %s",
    check_function=check_scaleio_storage_pool_totalrw,
    sections=["scaleio_storage_pool"],
    discovery_function=discover_scaleio_storage_pool,
    check_ruleset_name="diskstat",
    check_default_parameters={},
)


def check_scaleio_storage_pool_rebalancerw(
    item: str,
    params: Mapping[str, Any],
    section: ScaleioStoragePoolSection,
) -> CheckResult:
    if not (pool := section.get(item)):
        return

    yield from _check_scaleio_storage_pool_disks(
        params=params,
        pool_name=pool.name,
        disk_stats=pool.rebalance_io,
        value_store=get_value_store(),
    )


check_plugin_scaleio_storage_pool_rebalancerw = CheckPlugin(
    name="scaleio_storage_pool_rebalancerw",
    service_name="ScaleIO SP rebalance IO %s",
    sections=["scaleio_storage_pool"],
    check_function=check_scaleio_storage_pool_rebalancerw,
    discovery_function=discover_scaleio_storage_pool,
    check_ruleset_name="diskstat",
    check_default_parameters={},
)
