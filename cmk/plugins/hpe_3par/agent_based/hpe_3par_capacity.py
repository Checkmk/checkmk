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
    Result,
    Service,
    StringTable,
)
from cmk.plugins.hpe_3par.lib.agent_based import parse_3par
from cmk.plugins.lib.df import df_check_filesystem_single, FILESYSTEM_DEFAULT_PARAMS


@dataclass
class HPE3ParCapacity:
    name: str
    total_capacity: float
    free_capacity: float
    failed_capacity: float


HPE3ParCapacitySection = Mapping[str, HPE3ParCapacity]


def parse_hpe_3par_capacity(string_table: StringTable) -> HPE3ParCapacitySection:
    return {
        raw_name.replace("Capacity", ""): HPE3ParCapacity(
            name=raw_name.replace("Capacity", ""),
            total_capacity=float(raw_values["totalMiB"]),
            free_capacity=float(raw_values["freeMiB"]),
            failed_capacity=float(raw_values["failedCapacityMiB"]),
        )
        for raw_name, raw_values in parse_3par(string_table).items()
    }


agent_section_3par_capacity = AgentSection(
    name="3par_capacity",
    parse_function=parse_hpe_3par_capacity,
)


def discover_hpe_3par_capacity(section: HPE3ParCapacitySection) -> DiscoveryResult:
    for disk in section.values():
        if disk.total_capacity == 0:
            continue
        yield Service(item=disk.name)


def check_hpe_3par_capacity(
    item: str,
    params: Mapping[str, tuple[float, float]],
    section: HPE3ParCapacitySection,
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

    failed_bytes = disk.failed_capacity * 1024**2
    total_bytes = disk.total_capacity * 1024**2

    result, *_ignore = check_levels_v1(
        value=failed_bytes * 100.0 / total_bytes,
        levels_upper=params["failed_capacity_levels"],
        label="Failed",
        render_func=render.percent,
    )
    yield Result(
        state=result.state,
        summary=(f"{result.summary} - {render.bytes(failed_bytes)} of {render.bytes(total_bytes)}"),
    )


check_plugin_3par_capacity = CheckPlugin(
    name="3par_capacity",
    service_name="Capacity %s",
    check_function=check_hpe_3par_capacity,
    check_default_parameters={
        **FILESYSTEM_DEFAULT_PARAMS,
        "failed_capacity_levels": (0.0, 0.0),
    },
    check_ruleset_name="threepar_capacity",
    discovery_function=discover_hpe_3par_capacity,
)
