#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.df import df_check_filesystem_single, FILESYSTEM_DEFAULT_PARAMS
from cmk.plugins.lib.threepar import parse_3par

STATES = {
    1: State.OK,
    2: State.WARN,
    3: State.CRIT,
}

PROVISIONING_MAP = {
    1: "FULL",
    2: "TPVV",
    3: "SNP",
    4: "PEER",
    5: "UNKNOWN",
    6: "TDVV",
    7: "DDS",
}


@dataclass
class ThreePortVolume:
    name: str | None
    is_system_volume: bool
    total_capacity: float
    free_capacity: float
    deduplication: float | None
    compaction: float | None
    provisioning: float
    provisioning_type: str
    state: State
    wwn: str


ThreeParVolumeSection = Mapping[str, ThreePortVolume]


def parse_threepar_volumes(string_table: StringTable) -> ThreeParVolumeSection:
    threepar_volumes: MutableMapping[str, ThreePortVolume] = {}

    for volume in parse_3par(string_table).get("members", {}):
        total_capacity = float(volume["sizeMiB"])
        capacity_efficiency = volume.get(
            "capacityEfficiency"
        )  # Sometimes this section is not available
        threepar_volumes.setdefault(
            volume.get("name"),
            ThreePortVolume(
                name=volume.get("name"),
                is_system_volume=volume["policies"]["system"],
                total_capacity=total_capacity,
                free_capacity=total_capacity
                - (
                    volume["userSpace"]["usedMiB"]
                    if volume.get("userSpace")
                    else volume["totalUsedMiB"]
                ),
                deduplication=(
                    capacity_efficiency.get(
                        "deduplication"
                    )  # Will only be created if the capacityEfficiency section is available
                    if capacity_efficiency
                    else None
                ),
                compaction=(
                    capacity_efficiency.get("compaction") if capacity_efficiency else None
                ),  # Will only be created if the capacityEfficiency section is available
                provisioning=float(
                    (
                        volume["userSpace"]["rawReservedMiB"]
                        if volume.get("userSpace")
                        else volume.get("totalReservedMiB", 0)
                    )
                    * 1024**2
                ),
                provisioning_type=PROVISIONING_MAP[volume["provisioningType"]],
                state=STATES.get(volume["state"], State.UNKNOWN),
                wwn=volume["wwn"],
            ),
        )

    return threepar_volumes


agent_section_3par_volumes = AgentSection(
    name="3par_volumes",
    parse_function=parse_threepar_volumes,
)


def discover_threepar_volumes(section: ThreeParVolumeSection) -> DiscoveryResult:
    for volume in section.values():
        if not volume.is_system_volume and volume.name:
            yield Service(item=volume.name)


def check_threepar_volumes(
    item: str,
    params: Mapping[str, Any],
    section: ThreeParVolumeSection,
) -> CheckResult:
    if (volume := section.get(item)) is None:
        return

    yield from df_check_filesystem_single(
        value_store=get_value_store(),
        mountpoint=item,
        filesystem_size=volume.total_capacity,
        free_space=volume.free_capacity,
        reserved_space=0.0,
        inodes_total=None,
        inodes_avail=None,
        params=params,
    )

    if volume.deduplication is not None:
        yield Result(state=State.OK, summary=f"Dedup: {volume.deduplication}")

    if volume.compaction is not None:
        yield Result(state=State.OK, summary=f"Compact: {volume.compaction}")

    yield Result(
        state=volume.state,
        summary=f"Type: {volume.provisioning_type}, WWN: {volume.wwn}",
    )
    yield Metric(
        name="fs_provisioning",
        value=volume.provisioning,
    )


check_plugin_3par_volumes = CheckPlugin(
    name="3par_volumes",
    service_name="Volume %s",
    discovery_function=discover_threepar_volumes,
    check_function=check_threepar_volumes,
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
    check_ruleset_name="filesystem",
)
