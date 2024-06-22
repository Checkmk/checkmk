#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any, NamedTuple

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    RuleSetType,
    StringTable,
)
from cmk.plugins.lib.df import df_check_filesystem_list, df_discovery, FILESYSTEM_DEFAULT_PARAMS

# FS Types:
# AUTOMNT
# TFS
# ZFS
# NFS
# HFS


class MountPoint(NamedTuple):
    usage: tuple[str, float, float, float]
    options: set[str]


Section = Mapping[str, MountPoint]


_DF_ZOS_EXCLUDE_LIST = ["AUTOMNT", "TFS", "NFS"]


def parse_df_zos(string_table: StringTable) -> Section:
    section: dict[str, MountPoint] = {}
    usage: tuple[str, float, float, float] | None = None
    options: set[str] = set()

    for line in string_table:
        if line[0].startswith("#####"):
            # Add item for filesystem
            if usage and options:
                section[usage[0]] = MountPoint(usage, options)

            usage = None
            options = set()
        elif line[0].startswith("Filesystem"):
            # Ignore header line
            continue
        elif usage is None:
            usage = (line[5], float(line[1]) / 1024.0, float(line[3]) / 1024.0, 0.0)
        elif not options:
            # Second line: filesystem options
            for option in line:
                options.add(option.replace(",", ""))
            if "Read" in options and "Only" in options:
                options.remove("Read")
                options.remove("Only")
                options.add("ReadOnly")
    return section


agent_section_df_zos = AgentSection(
    name="df_zos",
    parse_function=parse_df_zos,
)


def discover_df_zos(params: Sequence[Mapping[str, Any]], section: Section) -> DiscoveryResult:
    yield from df_discovery(
        params,
        [
            item
            for item, mp in section.items()
            if "Read/Write" in mp.options and not mp.options.intersection(_DF_ZOS_EXCLUDE_LIST)
        ],
    )


def check_df_zos(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    yield from df_check_filesystem_list(
        value_store=get_value_store(),
        item=item,
        params=params,
        fslist_blocks=[mp.usage for mp in section.values()],
    )


check_plugin_df_zos = CheckPlugin(
    name="df_zos",
    service_name="Filesystem %s",
    discovery_function=discover_df_zos,
    discovery_ruleset_name="filesystem_groups",
    discovery_ruleset_type=RuleSetType.ALL,
    discovery_default_parameters={"groups": []},
    check_function=check_df_zos,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
