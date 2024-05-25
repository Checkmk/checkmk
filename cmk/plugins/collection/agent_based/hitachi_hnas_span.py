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
from cmk.plugins.lib import hitachi_hnas
from cmk.plugins.lib.df import (
    df_check_filesystem_list,
    df_discovery,
    FILESYSTEM_DEFAULT_PARAMS,
    FSBlock,
)

Section = Mapping[str, FSBlock]


def parse_hitachi_hnas_span(string_table: StringTable) -> Section:
    section = {}
    for id_, label, total_upper, total_lower, used_upper, used_lower in string_table:
        item = f"{id_} {label}"
        size_mb = (int(total_upper) * 2**32 + int(total_lower)) / 1024.0**2
        avail_mb = size_mb - (int(used_upper) * 2**32 + int(used_lower)) / 1024.0**2
        section[item] = (item, size_mb, avail_mb, 0.0)

    return section


def discover_hitachi_hnas_span(
    params: Sequence[Mapping[str, Any]], section: Section
) -> DiscoveryResult:
    yield from df_discovery(params, list(section))


def check_hitachi_hnas_span(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if (fs := section.get(item)) is None:
        return

    yield from df_check_filesystem_list(
        value_store=get_value_store(),
        item=item,
        params=params,
        fslist_blocks=[fs],
    )


snmp_section_hitachi_hnas_span = SimpleSNMPSection(
    name="hitachi_hnas_span",
    parse_function=parse_hitachi_hnas_span,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11096.6.1.1.6.4.2.1",
        oids=[
            "1",  # spanStatsSpanId
            "2",  # spanLabel
            "3",  # spanCapacityTotalUpper
            "4",  # spanCapacityTotalLower
            "5",  # spanCapacityUsedUpper
            "6",  # spanCapacityUsedLower
        ],
    ),
    detect=hitachi_hnas.DETECT,
)


check_plugin_hitachi_hnas_span = CheckPlugin(
    name="hitachi_hnas_span",
    service_name="Span %s",
    discovery_function=discover_hitachi_hnas_span,
    discovery_ruleset_name="filesystem_groups",
    discovery_ruleset_type=RuleSetType.ALL,
    discovery_default_parameters={"groups": []},
    check_function=check_hitachi_hnas_span,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
