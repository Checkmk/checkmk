#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any, NamedTuple

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Service,
    StringTable,
)


class LvmLvsEntry(NamedTuple):
    data: float
    meta: float


Section = Mapping[str, LvmLvsEntry]


def parse_lvm_lvs(string_table: StringTable) -> Section:
    possible_items = {f"{line[1]}/{line[4]}" for line in string_table if line[4] != ""}

    parsed = {}
    for line in string_table:
        item = f"{line[1]}/{line[0]}"
        if item not in possible_items:
            continue

        try:
            parsed[item] = LvmLvsEntry(data=float(line[6]), meta=float(line[7]))
        except (IndexError, ValueError):
            pass
    return parsed


def check_lvm_lvs(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if not (entry := section.get(item)):
        return

    yield from check_levels(
        entry.data,
        metric_name="data_usage",
        levels_upper=params["levels_data"],
        render_func=render.percent,
        label="Data usage",
    )
    yield from check_levels(
        entry.meta,
        metric_name="meta_usage",
        levels_upper=params["levels_meta"],
        render_func=render.percent,
        label="Meta usage",
    )


def discover_lvm_lvs(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


agent_section_lvm_lvs = AgentSection(
    name="lvm_lvs",
    parse_function=parse_lvm_lvs,
)


check_plugin_lvm_lvs = CheckPlugin(
    name="lvm_lvs",
    service_name="LVM LV Pool %s",
    discovery_function=discover_lvm_lvs,
    check_function=check_lvm_lvs,
    check_ruleset_name="lvm_lvs_pools",
    check_default_parameters={
        "levels_data": ("fixed", (80.0, 90.0)),
        "levels_meta": ("fixed", (80.0, 90.0)),
    },
)
