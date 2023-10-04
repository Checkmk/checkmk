# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel

from .agent_based_api.v1 import check_levels, Metric, register, render, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.df import (
    check_filesystem_levels,
    FILESYSTEM_DEFAULT_LEVELS,
    MAGIC_FACTOR_DEFAULT_PARAMS,
)


class Volume(BaseModel, frozen=True):
    virtual: float
    total_provisioned: float
    data_reduction: float
    unique: float
    snapshots: float


def parse_volume(string_table: StringTable) -> Mapping[str, Volume] | None:
    json_data = json.loads(string_table[0][0])
    if not (volumes := json_data.get("items")):
        return None

    return {item["name"]: Volume.parse_obj(item["space"]) for item in volumes}


register.agent_section(
    name="pure_storage_fa_volumes",
    parse_function=parse_volume,
)


def discover_volume_capacity(section: Mapping[str, Volume]) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_volume_capacity(
    item: str, params: Mapping[str, Any], section: Mapping[str, Volume]
) -> CheckResult:
    if (volume := section.get(item)) is None:
        return

    total_provisioned_mb = volume.total_provisioned / 1024.0**2
    free_space = volume.total_provisioned - volume.virtual

    yield from check_filesystem_levels(
        total_provisioned_mb,
        total_provisioned_mb,
        free_space / 1024.0**2,
        volume.virtual / 1024.0**2,
        params,
    )

    yield from check_levels(
        volume.data_reduction,
        metric_name="data_reduction",
        levels_lower=params.get("data_reduction"),
        render_func=lambda x: f"{x:.2f} to 1",
        label="Data reduction",
    )

    yield Result(state=State.OK, notice=f"Size: {render.bytes(volume.total_provisioned)}")
    yield Metric("fs_size", volume.total_provisioned, boundaries=(0, None))

    yield Result(
        state=State.OK, notice=f"Physical capacity used - volume: {render.bytes(volume.unique)}"
    )
    yield Metric("unique_size", volume.unique)

    yield Result(
        state=State.OK,
        notice=f"Physical capacity used - snapshots: {render.bytes(volume.snapshots)}",
    )
    yield Metric("snapshots_size", volume.snapshots)

    yield Result(
        state=State.OK, notice=f"Virtual capacity used - volume: {render.bytes(volume.virtual)}"
    )
    yield Metric("virtual_size", volume.virtual)


register.check_plugin(
    name="pure_storage_fa_volumes",
    service_name="Volume %s Capacity",
    discovery_function=discover_volume_capacity,
    check_function=check_volume_capacity,
    check_ruleset_name="pure_storage_capacity",
    check_default_parameters={
        **FILESYSTEM_DEFAULT_LEVELS,
        **MAGIC_FACTOR_DEFAULT_PARAMS,
    },
)
