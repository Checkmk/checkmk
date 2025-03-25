#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from dataclasses import dataclass

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    render,
    Service,
    StringTable,
)
from cmk.plugins.lib.df import df_check_filesystem_single, FILESYSTEM_DEFAULT_PARAMS
from cmk.plugins.lib.threepar import parse_3par


@dataclass
class ThreeParCapacity:
    name: str
    total_capacity: float
    free_capacity: float
    failed_capacity: float


ThreeParCapacitySection = Mapping[str, ThreeParCapacity]


def parse_threepar_capacity(string_table: StringTable) -> ThreeParCapacitySection:
    return {
        raw_name.replace("Capacity", ""): ThreeParCapacity(
            name=raw_name.replace("Capacity", ""),
            total_capacity=float(raw_values["totalMiB"]),
            free_capacity=float(raw_values["freeMiB"]),
            failed_capacity=float(raw_values["failedCapacityMiB"]),
        )
        for raw_name, raw_values in parse_3par(string_table).items()
    }


agent_section_3par_capacity = AgentSection(
    name="3par_capacity",
    parse_function=parse_threepar_capacity,
)


def discover_threepar_capacity(section: ThreeParCapacitySection) -> DiscoveryResult:
    for disk in section.values():
        if disk.total_capacity == 0:
            continue
        yield Service(item=disk.name)


def check_threepar_capacity(
    item: str,
    params: Mapping[str, tuple[float, float]],
    section: ThreeParCapacitySection,
) -> CheckResult:
    if (disk := section.get(item)) is None:
        return

    yield from df_check_filesystem_single(
        get_value_store(),
        item,
        disk.total_capacity,
        disk.free_capacity,
        disk.failed_capacity,
        None,
        None,
        params,
    )
    if disk.failed_capacity == 0.0:
        return

    yield from check_levels_v1(
        value=disk.failed_capacity / disk.total_capacity * 100,
        levels_upper=params.get("failed_capacity_levels", (0.0, 0.0)),
        label=f"{disk.failed_capacity} MB failed",
        render_func=render.percent,
    )


check_plugin_3par_capacity = CheckPlugin(
    name="3par_capacity",
    service_name="Capacity %s",
    check_function=check_threepar_capacity,
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
    check_ruleset_name="threepar_capacity",
    discovery_function=discover_threepar_capacity,
)
