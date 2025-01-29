#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.plugins.lib.couchbase import parse_couchbase_lines, Section

check_info = {}

DiscoveryResult = Iterable[tuple[str, dict]]


def discover_couchbase_nodes_items(section: Section) -> DiscoveryResult:
    yield from ((item, {}) for item, data in section.items() if "curr_items" in data)


def check_couchbase_nodes_items(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    active = data.get("curr_items")
    if active is not None:
        yield check_levels(
            active,
            "items_active",
            params.get("curr_items"),
            human_readable_func=str,
            infoname="Items in active vBuckets",
        )

    non_res = data.get("vb_active_num_non_resident")
    if non_res is not None:
        yield check_levels(
            non_res,
            "items_non_res",
            params.get("non_residents"),
            human_readable_func=str,
            infoname="Non-resident items",
        )

    total = data.get("curr_items_tot")
    if total is not None:
        yield check_levels(
            total,
            "items",
            params.get("curr_items_tot"),
            human_readable_func=str,
            infoname="Total items in vBuckets",
        )


check_info["couchbase_nodes_items"] = LegacyCheckDefinition(
    name="couchbase_nodes_items",
    parse_function=parse_couchbase_lines,
    service_name="Couchbase %s vBucket items",
    discovery_function=discover_couchbase_nodes_items,
    check_function=check_couchbase_nodes_items,
    check_ruleset_name="couchbase_items",
)
