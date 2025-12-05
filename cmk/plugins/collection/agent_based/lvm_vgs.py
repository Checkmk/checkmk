#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
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


def discover_lvm_vgs(section: StringTable) -> DiscoveryResult:
    for line in section:
        yield Service(item=line[0])


def check_lvm_vgs(item: str, params: Mapping[str, Any], section: StringTable) -> CheckResult:
    vglist = []
    for vg, _pvs, _lvs, _sns, _attr, size, free in section:
        size_mb = int(size) // 1024**2
        avail_mb = int(free) // 1024**2
        vglist.append((vg, size_mb, avail_mb, 0))
    yield from df_check_filesystem_list(get_value_store(), item, params, vglist)


def parse_lvm_vgs(string_table: StringTable) -> StringTable:
    return string_table


agent_section_lvm_vgs = AgentSection(
    name="lvm_vgs",
    parse_function=parse_lvm_vgs,
)

check_plugin_lvm_vgs = CheckPlugin(
    name="lvm_vgs",
    service_name="LVM VG %s",
    discovery_function=discover_lvm_vgs,
    check_function=check_lvm_vgs,
    check_ruleset_name="volume_groups",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
