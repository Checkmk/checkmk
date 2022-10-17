#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable

from .agent_based_api.v1 import register
from .utils.threepar import parse_3par

STATES = {
    1: 0,
    2: 1,
    3: 2,
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
    total_capacity: int
    free_capacity: int
    deduplication: float | None
    compaction: float | None
    provisioning: int
    provisioning_type: str
    state: int
    wwn: str


ThreeParVolumeSection = Mapping[str, ThreePortVolume]


def parse_threepar_volumes(string_table: StringTable) -> ThreeParVolumeSection:
    threepar_volumes: MutableMapping[str, ThreePortVolume] = {}

    for volume in parse_3par(string_table).get("members", {}):
        total_capacity = volume["sizeMiB"]
        capacity_efficiency = volume.get("capacityEfficiency")

        threepar_volumes.setdefault(
            volume.get("name"),
            ThreePortVolume(
                name=volume.get("name"),
                is_system_volume=volume["policies"]["system"],
                total_capacity=total_capacity,
                free_capacity=total_capacity - volume["userSpace"]["usedMiB"],
                deduplication=capacity_efficiency.get("deduplication")
                if capacity_efficiency
                else None,
                compaction=capacity_efficiency.get("compaction") if capacity_efficiency else None,
                provisioning=volume["userSpace"]["rawReservedMiB"] * 1024**2,
                provisioning_type=PROVISIONING_MAP[volume["provisioningType"]],
                state=STATES.get(volume["state"], 3),
                wwn=volume["wwn"],
            ),
        )

    return threepar_volumes


register.agent_section(
    name="3par_volumes",
    parse_function=parse_threepar_volumes,
)
