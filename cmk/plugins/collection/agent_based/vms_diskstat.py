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
    df_check_filesystem_single,
    df_discovery,
    FILESYSTEM_DEFAULT_PARAMS,
    FSBlock,
)

Section = Mapping[str, FSBlock]

# Example output from agent:
# <<<vms_diskstat>>>
# $1$DGA1122: TEST_WORK 1171743836 1102431184 0.00
# DSA1: SHAD_1 66048000 58815666 0.00
# DSA2: SHAD_2 66048000 47101824 0.07
# DSA3: SHAD_3 66048000 46137546 1.57
# DSA4: SHAD_4 66048000 36087093 0.00
# DSA5: SHAD_5 66048000 32449914 0.00
# $1$DGA1123: TEST_WORK 2171743836 1102431184 0.00
# $1$DGA1124: TEMP_02 3171743836 102431184 1.10
# $1$DGA1125: DATA_01 1171743836 202431184 0.20


def _mb(raw: str) -> float:
    return int(raw) * 512 / (1024.0 * 1024.0)


def parse_vms_diskstat(string_table: StringTable) -> Section:
    return {
        label: (label, _mb(size), _mb(avail), 0)
        # Note that items can repeat, as seen in the output above.
        # Prior to this refactoring, the check function picked the first occurring item.
        # We stick to that for now, hence the "reversed".
        # I'm not sure it makes sense :-(
        for _device, label, size, avail, _ios in reversed(string_table)
    }


agent_section_vms_diskstat = AgentSection(
    name="vms_diskstat",
    parse_function=parse_vms_diskstat,
)


def discover_vms_diskstat_df(
    params: Sequence[Mapping[str, Any]], section: Section
) -> DiscoveryResult:
    yield from df_discovery(params, section)


def check_vms_diskstat_df(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if (volume := section.get(item)) is None:
        return
    yield from df_check_filesystem_single(get_value_store(), *volume, None, None, params)


check_plugin_vms_diskstat_df = CheckPlugin(
    name="vms_diskstat_df",
    sections=["vms_diskstat"],
    service_name="Filesystem %s",
    discovery_function=discover_vms_diskstat_df,
    discovery_default_parameters={"groups": []},
    discovery_ruleset_name="filesystem_groups",
    discovery_ruleset_type=RuleSetType.ALL,
    check_function=check_vms_diskstat_df,
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
    check_ruleset_name="filesystem",
)
