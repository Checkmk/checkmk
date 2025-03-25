#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.df import (
    check_filesystem_levels,
    FILESYSTEM_DEFAULT_LEVELS,
    MAGIC_FACTOR_DEFAULT_PARAMS,
)


class Array(BaseModel, frozen=True):
    total_physical: float
    capacity: float
    data_reduction: float
    unique: float
    snapshots: float
    shared: float
    system: float
    replication: float


def parse_array(string_table: StringTable) -> Array | None:
    json_data = json.loads(string_table[0][0])
    if not (arrays := json_data.get("items")):
        return None

    # there should always be only one array
    array = arrays[0]

    return Array(
        total_physical=array["space"]["total_physical"],
        capacity=array["capacity"],
        data_reduction=array["space"]["data_reduction"],
        unique=array["space"]["unique"],
        snapshots=array["space"]["snapshots"],
        shared=array["space"]["shared"],
        system=array["space"]["system"],
        replication=array["space"]["replication"],
    )


agent_section_pure_storage_fa_arrays = AgentSection(
    name="pure_storage_fa_arrays",
    parse_function=parse_array,
)


def discover_overall_capacity(section: Array) -> DiscoveryResult:
    yield Service(item="Overall")


def check_overall_capacity(item: str, params: Mapping[str, Any], section: Array) -> CheckResult:
    capacity_mb = section.capacity / 1024.0**2
    free_space = section.capacity - section.total_physical

    yield from check_filesystem_levels(
        capacity_mb,
        capacity_mb,
        free_space / 1024.0**2,
        section.total_physical / 1024.0**2,
        params,
    )

    yield Metric("fs_size", section.capacity, boundaries=(0, None))

    yield from check_levels_v1(
        section.data_reduction,
        metric_name="data_reduction",
        levels_lower=params.get("data_reduction"),
        render_func=lambda x: f"{x:.2f} to 1",
        label="Data reduction",
    )

    yield Result(state=State.OK, notice=f"Unique: {render.bytes(section.unique)}")
    yield Metric("unique_size", section.unique)

    yield Result(state=State.OK, notice=f"Snapshots: {render.bytes(section.snapshots)}")
    yield Metric("snapshots_size", section.snapshots)

    yield Result(state=State.OK, notice=f"Shared: {render.bytes(section.shared)}")
    yield Metric("shared_size", section.shared)

    yield Result(state=State.OK, notice=f"System: {render.bytes(section.system)}")
    yield Metric("system_size", section.system)

    yield Result(state=State.OK, notice=f"Replication: {render.disksize(section.replication)}")
    yield Metric("replication_size", section.replication)

    yield Result(state=State.OK, notice=f"Empty: {render.bytes(free_space)}")


check_plugin_pure_storage_fa_arrays = CheckPlugin(
    name="pure_storage_fa_arrays",
    service_name="%s Capacity",
    discovery_function=discover_overall_capacity,
    check_function=check_overall_capacity,
    check_ruleset_name="pure_storage_capacity",
    check_default_parameters={
        **FILESYSTEM_DEFAULT_LEVELS,
        **MAGIC_FACTOR_DEFAULT_PARAMS,
    },
)
