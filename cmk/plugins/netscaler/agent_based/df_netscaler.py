#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    RuleSetType,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.df import (
    df_check_filesystem_list,
    df_discovery,
    EXCLUDED_MOUNTPOINTS,
    FILESYSTEM_DEFAULT_PARAMS,
    FSBlocks,
)

from .lib import SNMP_DETECT

#
# Example Output:
# .1.3.6.1.4.1.5951.4.1.1.41.8.1.1.4.47.118.97.114  "/var"
# .1.3.6.1.4.1.5951.4.1.1.41.8.1.1.6.47.102.108.97.115.104  "/flash"
# .1.3.6.1.4.1.5951.4.1.1.41.8.1.2.4.47.118.97.114  96133
# .1.3.6.1.4.1.5951.4.1.1.41.8.1.2.6.47.102.108.97.115.104  7976
# .1.3.6.1.4.1.5951.4.1.1.41.8.1.3.4.47.118.97.114  87418
# .1.3.6.1.4.1.5951.4.1.1.41.8.1.3.6.47.102.108.97.115.104  7256


def parse_df_netscaler(string_table: StringTable) -> FSBlocks:
    return [(name, float(size), float(avail), 0.0) for name, size, avail in string_table]


snmp_section_df_netscaler = SimpleSNMPSection(
    name="df_netscaler",
    parse_function=parse_df_netscaler,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.5951.4.1.1.41.8.1",
        oids=[
            "1",  # sysHealthDiskName
            "2",  # sysHealthDiskSize
            "3",  # sysHealthDiskAvail
        ],
    ),
    detect=SNMP_DETECT,
)


def discover_df_netscaler(
    params: Sequence[Mapping[str, Any]], section: FSBlocks
) -> DiscoveryResult:
    yield from df_discovery(
        params,
        [
            name
            for name, size, *_rest in section
            if size and size > 0 and name not in EXCLUDED_MOUNTPOINTS
        ],
    )


def check_df_netscaler(item: str, params: Mapping[str, Any], section: FSBlocks) -> CheckResult:
    yield from df_check_filesystem_list(
        value_store=get_value_store(),
        item=item,
        params=params,
        fslist_blocks=section,
    )


check_plugin_df_netscaler = CheckPlugin(
    name="df_netscaler",
    service_name="Filesystem %s",
    discovery_function=discover_df_netscaler,
    discovery_ruleset_name="filesystem_groups",
    discovery_ruleset_type=RuleSetType.ALL,
    discovery_default_parameters={"groups": []},
    check_function=check_df_netscaler,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
