#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import Any, Literal

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
)
from cmk.plugins.couchbase.lib import parse_couchbase_lines, Section


def _levels_upper(
    levels: tuple[int, int] | None,
) -> tuple[Literal["fixed"], tuple[int, int]] | None:
    return ("fixed", levels) if levels is not None else None


def discover_couchbase_nodes_items(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item, data in section.items() if "curr_items" in data)


def check_couchbase_nodes_items(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if not (data := section.get(item)):
        return

    active = data.get("curr_items")
    if active is not None:
        yield from check_levels(
            active,
            levels_upper=_levels_upper(params.get("curr_items")),
            metric_name="items_active",
            render_func=str,
            label="Items in active vBuckets",
        )

    non_res = data.get("vb_active_num_non_resident")
    if non_res is not None:
        yield from check_levels(
            non_res,
            levels_upper=_levels_upper(params.get("non_residents")),
            metric_name="items_non_res",
            render_func=str,
            label="Non-resident items",
        )

    total = data.get("curr_items_tot")
    if total is not None:
        yield from check_levels(
            total,
            levels_upper=_levels_upper(params.get("curr_items_tot")),
            metric_name="items",
            render_func=str,
            label="Total items in vBuckets",
        )


agent_section_couchbase_nodes_items = AgentSection(
    name="couchbase_nodes_items",
    parse_function=parse_couchbase_lines,
)


check_plugin_couchbase_nodes_items = CheckPlugin(
    name="couchbase_nodes_items",
    service_name="Couchbase %s vBucket items",
    discovery_function=discover_couchbase_nodes_items,
    check_function=check_couchbase_nodes_items,
    check_ruleset_name="couchbase_items",
    check_default_parameters={},
)
