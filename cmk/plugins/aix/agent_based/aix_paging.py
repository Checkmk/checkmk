#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import contextlib
from collections.abc import Mapping
from typing import Any, NamedTuple

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    IgnoreResultsError,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.df import df_check_filesystem_single, FILESYSTEM_DEFAULT_PARAMS

# example output
# <<<aix_paging>>>
# Page Space      Physical Volume   Volume Group    Size %Used   Active    Auto    Type   Chksum
# hd6                   hdisk11                rootvg       10240MB    23        yes        yes       lv       0


class AIXPaging(NamedTuple):
    group: str
    size_mb: int
    usage_perc: int
    active: str
    auto: str
    type_: str


type Section = Mapping[str, AIXPaging]


def parse_aix_paging(string_table: StringTable) -> Section:
    map_type = {
        "lv": "logical volume",
        "nfs": "NFS",
    }

    parsed: dict[str, AIXPaging] = {}
    if len(string_table) <= 1:
        return parsed

    # First line is the header
    for line in string_table[1:]:
        try:
            # Always given in MB, eg. 1234MB
            size = int(line[3][:-2])
        except ValueError:
            continue
        try:
            usage = int(line[4])
        except ValueError:
            continue
        paging_type = map_type.get(line[7], f"unknown[{line[7]}]")
        parsed.setdefault(
            f"{line[0]}/{line[1]}",
            AIXPaging(line[2], size, usage, line[5], line[6], paging_type),
        )
    return parsed


def check_aix_paging(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return
    avail_mb = data.size_mb * (1 - data.usage_perc / 100.0)
    with contextlib.suppress(IgnoreResultsError):
        yield from df_check_filesystem_single(
            get_value_store(), item, data.size_mb, avail_mb, 0, None, None, params
        )
    yield Result(
        state=State.OK, summary=f"Active: {data.active}, Auto: {data.auto}, Type: {data.type_}"
    )


def discover_aix_paging(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


agent_section_aix_paging = AgentSection(
    name="aix_paging",
    parse_function=parse_aix_paging,
)


check_plugin_aix_paging = CheckPlugin(
    name="aix_paging",
    service_name="Page Space %s",
    discovery_function=discover_aix_paging,
    check_function=check_aix_paging,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
