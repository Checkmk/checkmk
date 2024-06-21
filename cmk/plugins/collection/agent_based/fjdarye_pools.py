#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from time import time
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    equals,
    get_value_store,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.df import df_check_filesystem_single, FILESYSTEM_DEFAULT_PARAMS


@dataclass(frozen=True, kw_only=True)
class Pool:
    capacity: float
    usage: float
    available: float


def parse_fjdarye_pools(string_table: StringTable) -> dict[str, Pool]:
    pools = {}

    for pool_id, raw_capacity, raw_usage in string_table:
        try:
            capacity = float(raw_capacity)
            usage = float(raw_usage)
        except ValueError:
            continue

        pools[pool_id] = Pool(
            capacity=capacity,
            usage=usage,
            available=capacity - usage,
        )

    return pools


snmp_section_fjdarye_pools_150 = SimpleSNMPSection(
    # 150 does not refer to a specific device model, but to the OID
    # this section applies to a range of models (see AF250S2.pdf in SUP-16226):
    # ETERNUS AF250 S2/AF650S2
    # ETERNUS AF250/AF650
    # ETERNUS DX200F All-Flash Arrays
    # etc.
    name="fjdarye_pools_150",
    parsed_section_name="fjdarye_pools",
    parse_function=parse_fjdarye_pools,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.211.1.21.1.150.14.5.2.1",
        oids=[
            "1",  # fjdaryMgtTpPoolNumber
            "3",  # fjdaryMgtTpPoolTotalCapacity
            "4",  # fjdaryMgtTpPoolUsedCapacity
        ],
    ),
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.211.1.21.1.150"),
)


snmp_section_fjdarye_pools_153 = SimpleSNMPSection(
    # 153 does not refer to a specific device model, but to the OID
    # this section applies to a range of models (see AF250S3.pdf in SUP-16226):
    # ETERNUS AF150 S3/AF250 S3
    # ETERNUS AF650 S3 All-Flash Arrays
    # ETERNUS DX60 S5/DX100 S5/DX200 S5
    # etc.
    name="fjdarye_pools_153",
    parsed_section_name="fjdarye_pools",
    parse_function=parse_fjdarye_pools,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.211.1.21.1.153.14.5.2.1",
        oids=[
            "1",  # fjdaryMgtTpPoolNumber
            "3",  # fjdaryMgtTpPoolTotalCapacity
            "4",  # fjdaryMgtTpPoolUsedCapacity
        ],
    ),
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.211.1.21.1.153"),
)


def discover_fjdarye_pools(section: Mapping[str, Pool]) -> DiscoveryResult:
    for pool in section:
        yield Service(item=pool)


def check_fjdarye_pools(
    item: str, params: Mapping[str, Any], section: Mapping[str, Pool]
) -> CheckResult:
    if (pool := section.get(item)) is None:
        return
    yield from _check_fjdarye_pools(
        item=item,
        params=params,
        pool=pool,
        value_store=get_value_store(),
        timestamp=time(),
    )


def _check_fjdarye_pools(
    *,
    item: str,
    params: Mapping[str, Any],
    pool: Pool,
    value_store: MutableMapping[str, Any],
    timestamp: float,
) -> CheckResult:
    yield from df_check_filesystem_single(
        value_store=value_store,
        mountpoint=item,
        filesystem_size=pool.capacity,
        free_space=pool.available,
        reserved_space=0.0,
        inodes_total=None,
        inodes_avail=None,
        params=params,
        this_time=timestamp,
    )


check_plugin_fjdarye_pools = CheckPlugin(
    name="fjdarye_pools",
    service_name="Thin Provisioning Pool %s",
    discovery_function=discover_fjdarye_pools,
    check_function=check_fjdarye_pools,
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
    check_ruleset_name="filesystem",
)
