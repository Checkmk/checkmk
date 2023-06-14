#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import check_levels, discover, get_parsed_item_data, LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.utils.couchbase import parse_couchbase_lines


@get_parsed_item_data
def check_couchbase_buckets_cache(_item, params, data):
    miss_rate = data.get("ep_cache_miss_rate")
    if miss_rate is not None:
        yield check_levels(
            miss_rate,
            "cache_misses_rate",
            params.get("cache_misses"),
            human_readable_func=str,
            unit="/s",
            infoname="Cache misses",
        )


check_info["couchbase_buckets_cache"] = LegacyCheckDefinition(
    parse_function=parse_couchbase_lines,
    discovery_function=discover(lambda k, v: "ep_cache_miss_rate" in v),
    check_function=check_couchbase_buckets_cache,
    service_name="Couchbase Bucket %s Cache",
    check_ruleset_name="couchbase_cache",
)
