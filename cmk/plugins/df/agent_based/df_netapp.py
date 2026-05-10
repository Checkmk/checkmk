#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    all_of,
    any_of,
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    exists,
    get_value_store,
    not_exists,
    RuleSetType,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.df import (
    df_check_filesystem_list,
    df_discovery,
    FILESYSTEM_DEFAULT_PARAMS,
    FSBlocks,
)


def parse_df_netapp(string_table: StringTable) -> FSBlocks:
    section = []
    for name, size_kb, used_kb in string_table:
        if not size_kb:
            continue
        size_mb = float(size_kb) / 1024.0
        section.append((name, size_mb, size_mb - float(used_kb) / 1024.0, 0.0))
    return section


IS_NETAPP_FILER = any_of(
    contains(".1.3.6.1.2.1.1.1.0", "ontap"),
    contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.789"),
)


snmp_section_df_netapp = SimpleSNMPSection(
    name="df_netapp",
    parse_function=parse_df_netapp,
    fetch=SNMPTree(base=".1.3.6.1.4.1.789.1.5.4.1", oids=["2", "29", "30"]),
    detect=all_of(IS_NETAPP_FILER, exists(".1.3.6.1.4.1.789.1.5.4.1.29.*")),
)


snmp_section_df_netapp32 = SimpleSNMPSection(
    name="df_netapp32",
    parsed_section_name="df_netapp",
    parse_function=parse_df_netapp,
    fetch=SNMPTree(base=".1.3.6.1.4.1.789.1.5.4.1", oids=["2", "3", "4"]),
    detect=all_of(IS_NETAPP_FILER, not_exists(".1.3.6.1.4.1.789.1.5.4.1.29.*")),
)


def discover_df_netapp(params: Sequence[Mapping[str, Any]], section: FSBlocks) -> DiscoveryResult:
    yield from df_discovery(
        params,
        [
            volume
            for volume, size, *_rest in section
            if size and size > 0  # Exclude filesystems with zero size (some snapshots)
        ],
    )


def check_df_netapp(item: str, params: Mapping[str, Any], section: FSBlocks) -> CheckResult:
    fslist = [mp for mp in section if "patterns" in params or item == mp[0]]
    yield from df_check_filesystem_list(
        value_store=get_value_store(),
        item=item,
        params=params,
        fslist_blocks=fslist,
    )


check_plugin_df_netapp = CheckPlugin(
    name="df_netapp",
    service_name="Filesystem %s",
    discovery_function=discover_df_netapp,
    discovery_ruleset_name="filesystem_groups",
    discovery_ruleset_type=RuleSetType.ALL,
    discovery_default_parameters={"groups": []},
    check_function=check_df_netapp,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
