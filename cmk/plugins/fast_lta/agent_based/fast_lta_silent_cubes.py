#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    all_of,
    any_of,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    exists,
    get_value_store,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    StringTable,
)
from cmk.plugins.lib.df import df_check_filesystem_list, FILESYSTEM_DEFAULT_PARAMS, FSBlock


def parse_fast_lta_silent_cubes(string_table: StringTable) -> StringTable:
    return string_table


def discover_fast_lta_silent_cubes_capacity(section: StringTable) -> DiscoveryResult:
    if len(section) > 0 and len(section[0]) > 1:
        yield Service(item="Total")


def check_fast_lta_silent_cubes_capacity(
    item: str, params: Mapping[str, Any], section: StringTable
) -> CheckResult:
    fslist: list[FSBlock] = []
    for total, used in section:
        total_bytes = int(total)
        used_bytes = int(used)
        fslist.append((item, total_bytes / 1048576.0, (total_bytes - used_bytes) / 1048576.0, 0))

    yield from df_check_filesystem_list(
        value_store=get_value_store(),
        item=item,
        params=params,
        fslist_blocks=fslist,
    )


snmp_section_fast_lta_silent_cubes = SimpleSNMPSection(
    name="fast_lta_silent_cubes",
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.8072.3.2.10"),
        any_of(
            exists(".1.3.6.1.4.1.27417.3.2"),
            exists(".1.3.6.1.4.1.27417.3.2.0"),
        ),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.27417.3",
        oids=["2", "3"],
    ),
    parse_function=parse_fast_lta_silent_cubes,
)

check_plugin_fast_lta_silent_cubes_capacity = CheckPlugin(
    name="fast_lta_silent_cubes_capacity",
    sections=["fast_lta_silent_cubes"],
    service_name="Fast LTA SC Capacity %s",
    discovery_function=discover_fast_lta_silent_cubes_capacity,
    check_function=check_fast_lta_silent_cubes_capacity,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
