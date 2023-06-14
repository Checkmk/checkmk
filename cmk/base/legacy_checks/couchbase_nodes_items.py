#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import check_levels, discover, get_parsed_item_data, LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.utils.couchbase import parse_couchbase_lines


@get_parsed_item_data
def check_couchbase_nodes_items(_item, params, data):
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
    parse_function=parse_couchbase_lines,
    discovery_function=discover(lambda _k, v: "curr_items" in v),
    check_function=check_couchbase_nodes_items,
    service_name="Couchbase %s vBucket items",
    check_ruleset_name="couchbase_items",
)
