#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from contextlib import suppress
from typing import Any, List, Mapping, MutableMapping, NamedTuple

from .agent_based_api.v1 import equals, get_value_store, register, Service, SNMPTree
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.df import df_check_filesystem_single, FILESYSTEM_DEFAULT_PARAMS

FJDARYE_SUPPORTED_DEVICE = ".1.3.6.1.4.1.211.1.21.1.150"  # fjdarye500


class PoolEntry(NamedTuple):
    capacity: float
    usage: float
    available: float


FjdaryePoolsSection = Mapping[str, PoolEntry]


def _to_float(value: str) -> float | None:
    with suppress(ValueError):
        return float(value)
    return None


def parse_fjdarye_pools(string_table: List[StringTable]) -> FjdaryePoolsSection:
    pools: MutableMapping[str, PoolEntry] = {}

    if not string_table:
        return pools

    for pool_id, capacity, usage in string_table[0]:
        pool_capacity = _to_float(capacity)
        pool_usage = _to_float(usage)

        if pool_capacity is None or pool_usage is None:
            continue

        pools[pool_id] = PoolEntry(
            capacity=pool_capacity, usage=pool_usage, available=pool_capacity - pool_usage
        )

    return pools


register.snmp_section(
    name="fjdarye_pools",
    parse_function=parse_fjdarye_pools,
    fetch=[
        SNMPTree(
            base=f"{FJDARYE_SUPPORTED_DEVICE}.14.5.2.1",
            oids=[
                "1",  # fjdaryMgtTpPoolNumber
                "3",  # fjdaryMgtTpPoolTotalCapacity
                "4",  # fjdaryMgtTpPoolUsedCapacity
            ],
        )
    ],
    detect=equals(".1.3.6.1.2.1.1.2.0", FJDARYE_SUPPORTED_DEVICE),
)


def discover_fjdarye_pools(section: FjdaryePoolsSection) -> DiscoveryResult:
    for pool in section:
        yield Service(item=pool)


def check_fjdarye_pools(
    item: str, params: Mapping[str, Any], section: FjdaryePoolsSection
) -> CheckResult:
    if (pool := section.get(item)) is None:
        return

    yield from df_check_filesystem_single(
        value_store=get_value_store(),
        mountpoint=item,
        filesystem_size=pool.capacity,
        free_space=pool.available,
        reserved_space=0.0,
        inodes_total=None,
        inodes_avail=None,
        params=params,
    )


register.check_plugin(
    name="fjdarye_pools",
    service_name="Thin Provisioning Pool %s",
    discovery_function=discover_fjdarye_pools,
    check_function=check_fjdarye_pools,
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
    check_ruleset_name="filesystem",
)
