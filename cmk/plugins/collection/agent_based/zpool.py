#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    RuleSetType,
    StringTable,
)
from cmk.plugins.lib.df import (
    df_check_filesystem_list,
    df_discovery,
    FILESYSTEM_DEFAULT_PARAMS,
    FSBlock,
)

Section = Mapping[str, FSBlock]

# NAME    SIZE  ALLOC   FREE  CAP  HEALTH  ALTROOT
# app02  39.8G  14.1G  25.6G  35%  ONLINE  -
# rpool  39.8G  32.9G  6.81G  82%  ONLINE  -

# Or also:
# NAME        SIZE   USED  AVAIL    CAP  HEALTH  ALTROOT
# sth_ds      278G   127G   151G    45%  ONLINE  -


def _canonize_header_entry(entry: str) -> str:
    if entry == "used":
        return "alloc"
    if entry == "avail":
        return "free"
    return entry


# this belongs to the parse function.
def _mb(val: str) -> float:
    idx = None
    # split number from unit
    for idx, ch in enumerate(val):
        if ch not in "0123456789.-":
            break
    num = float(val[:idx])
    unit_str = val[idx:].lstrip().lower()
    unit = ["b", "k", "m", "g", "t", "p"].index(unit_str)

    return num * (1024 ** (unit - 2))


def parse_zpool(string_table: StringTable) -> Section | None:
    if not string_table:
        return None
    raw_header, *content = string_table

    header = [_canonize_header_entry(item.lower()) for item in raw_header]
    return {
        line[0]: (line[0], _mb(entry["size"]), _mb(entry["free"]), 0)
        for line in content
        if (entry := dict(zip(header, line)))
    }


agent_section_zpool = AgentSection(
    name="zpool",
    parse_function=parse_zpool,
)


def discover_zpool(params: Sequence[Mapping[str, Any]], section: Section) -> DiscoveryResult:
    yield from df_discovery(params, section)


def check_zpool(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    yield from df_check_filesystem_list(
        value_store=get_value_store(),
        item=item,
        params=params,
        fslist_blocks=list(section.values()),
    )


check_plugin_zpool = CheckPlugin(
    name="zpool",
    service_name="Storage Pool %s",
    discovery_function=discover_zpool,
    discovery_default_parameters={"groups": []},
    discovery_ruleset_name="filesystem_groups",
    discovery_ruleset_type=RuleSetType.ALL,
    check_function=check_zpool,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
