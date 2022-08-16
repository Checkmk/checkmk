#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping, MutableMapping

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)

from .agent_based_api.v1 import get_value_store, register, render, Result, Service, State
from .utils.df import df_check_filesystem_single, FILESYSTEM_DEFAULT_PARAMS
from .utils.scaleio import convert_scaleio_space, parse_scaleio, ScaleioSection

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


def parse_scaleio_storage_pool(string_table: StringTable) -> ScaleioSection:
    return parse_scaleio(string_table, "STORAGE_POOL")


register.agent_section(name="scaleio_storage_pool", parse_function=parse_scaleio_storage_pool)


def discover_scaleio_storage_pool(section: ScaleioSection) -> DiscoveryResult:
    for pool in section:
        yield Service(item=pool)


def _check_scaleio_storage_pool(
    item: str,
    params: Mapping[str, Any],
    section: ScaleioSection,
    value_store: MutableMapping[str, Any],
) -> CheckResult:
    if not (storage_pool := section.get(item)):
        return

    unit = storage_pool["MAX_CAPACITY_IN_KB"][1]
    total = convert_scaleio_space(unit, float(storage_pool["MAX_CAPACITY_IN_KB"][0]))
    free = convert_scaleio_space(unit, float(storage_pool["UNUSED_CAPACITY_IN_KB"][0]))

    yield from df_check_filesystem_single(
        value_store=value_store,
        mountpoint=item,
        filesystem_size=total,
        free_space=free,
        reserved_space=0.0,
        inodes_avail=None,
        inodes_total=None,
        params=params,
    )

    if (failed_value := float(storage_pool["FAILED_CAPACITY_IN_KB"][0])) > 0:
        yield Result(state=State.CRIT, summary=f"Failed Capacity: {render.bytes(failed_value)}")


def check_scaleio_storage_pool(
    item: str, params: Mapping[str, Any], section: ScaleioSection
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
