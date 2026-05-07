#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Service,
    StringTable,
)
from cmk.plugins.lib.df import df_check_filesystem_list, FILESYSTEM_DEFAULT_PARAMS


@dataclass
class VolumeGroup:
    name: str
    size: int
    free: int


type Section = Sequence[VolumeGroup]


def parse_lvm_vgs(string_table: StringTable) -> Section:
    return [
        VolumeGroup(vg, int(size), int(free))
        for vg, _pvs, _lvs, _sns, _attr, size, free in string_table
    ]


agent_section_lvm_vgs = AgentSection(
    name="lvm_vgs",
    parse_function=parse_lvm_vgs,
)


def discover_lvm_vgs(section: Section) -> DiscoveryResult:
    for vg in section:
        yield Service(item=vg.name)


def check_lvm_vgs(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    yield from df_check_filesystem_list(
        value_store=get_value_store(),
        item=item,
        params=params,
        fslist_blocks=[(vg.name, vg.size // 1024**2, vg.free // 1024**2, 0) for vg in section],
    )


check_plugin_lvm_vgs = CheckPlugin(
    name="lvm_vgs",
    service_name="LVM VG %s",
    discovery_function=discover_lvm_vgs,
    check_function=check_lvm_vgs,
    check_ruleset_name="volume_groups",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
