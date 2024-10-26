#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.plugins.lib.couchbase import parse_couchbase_lines, Section

check_info = {}

DiscoveryResult = Iterable[tuple[str, dict]]


def discover_couchbase_buckets_cache(section: Section) -> DiscoveryResult:
    yield from ((item, {}) for item, data in section.items() if "ep_cache_miss_rate" in data)


def check_couchbase_buckets_cache(item, params, parsed):
    if not (data := parsed.get(item)):
        return
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
    name="couchbase_buckets_cache",
    parse_function=parse_couchbase_lines,
    service_name="Couchbase Bucket %s Cache",
    discovery_function=discover_couchbase_buckets_cache,
    check_function=check_couchbase_buckets_cache,
    check_ruleset_name="couchbase_cache",
)
