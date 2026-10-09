#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Sequence
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    AgentSection,
    InventoryPlugin,
    InventoryResult,
    StringTable,
    TableRow,
)


@dataclass(frozen=True, kw_only=True)
class WanAccelerator:
    """Mirrors the VBR REST API's WanAcceleratorModel
    (GET /api/v1/backupInfrastructure/wanAccelerators)."""

    name: str
    description: str
    traffic_port: int
    streams_count: int
    high_bandwidth_mode_enabled: bool
    cache_folder: str
    cache_size: int


Section = Sequence[WanAccelerator]

# Decimal prefixes, as assumed for processingRate in veeam_backups
_SIZE_UNIT_FACTORS = {
    "B": 1,
    "KB": 1_000,
    "MB": 1_000_000,
    "GB": 1_000_000_000,
    "TB": 1_000_000_000_000,
    "PB": 1_000_000_000_000_000,
}


def parse_veeam_wan_accelerators(string_table: StringTable) -> Section:
    accelerators = []
    for line in string_table:
        accelerator = json.loads(line[0])
        server = accelerator["server"]
        cache = accelerator["cache"]
        accelerators.append(
            WanAccelerator(
                name=accelerator["name"],
                description=server["description"],
                traffic_port=server["trafficPort"],
                streams_count=server["streamsCount"],
                high_bandwidth_mode_enabled=server["highBandwidthModeEnabled"],
                cache_folder=cache["cacheFolder"],
                cache_size=cache["cacheSize"] * _SIZE_UNIT_FACTORS[cache["cacheSizeUnit"]],
            )
        )
    return accelerators


agent_section_veeam_wan_accelerators = AgentSection(
    name="veeam_wan_accelerators",
    parse_function=parse_veeam_wan_accelerators,
)


def inventory_veeam_wan_accelerators(section: Section) -> InventoryResult:
    for accelerator in section:
        yield TableRow(
            path=["software", "applications", "veeam", "wan_accelerators"],
            key_columns={"name": accelerator.name},
            inventory_columns={
                "description": accelerator.description,
                "traffic_port": accelerator.traffic_port,
                "streams_count": accelerator.streams_count,
                "high_bandwidth_mode_enabled": accelerator.high_bandwidth_mode_enabled,
                "cache_folder": accelerator.cache_folder,
                "cache_size": accelerator.cache_size,
            },
        )


inventory_plugin_veeam_wan_accelerators = InventoryPlugin(
    name="veeam_wan_accelerators",
    sections=["veeam_wan_accelerators"],
    inventory_function=inventory_veeam_wan_accelerators,
)
