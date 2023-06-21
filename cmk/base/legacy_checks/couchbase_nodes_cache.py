#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time
from collections.abc import Iterable

from cmk.base.check_api import check_levels, get_rate, LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import render
from cmk.base.plugins.agent_based.utils.couchbase import parse_couchbase_lines, Section

DiscoveryResult = Iterable[tuple[str, dict]]


def discover_couchbase_nodes_cache(section: Section) -> DiscoveryResult:
    yield from (
        (item, {})
        for item, data in section.items()
        if "get_hits" in data and "ep_bg_fetched" in data
    )


def check_couchbase_nodes_cache(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    misses = data.get("ep_bg_fetched")
    hits = data.get("get_hits")
    if None in (misses, hits):
        return
    total = misses + hits
    hit_perc = (hits / float(total)) * 100.0 if total != 0 else 100.0
    miss_rate = get_rate("%s.cache_misses" % item, time.time(), misses)

    yield check_levels(
        miss_rate,
        "cache_misses_rate",
        params.get("cache_misses"),
        human_readable_func=str,
        unit="/s",
        infoname="Cache misses",
    )

    yield check_levels(
        hit_perc,
        "cache_hit_ratio",
        (None, None) + params.get("cache_hits", (None, None)),
        human_readable_func=render.percent,
        infoname="Cache hits",
        boundaries=(0, 100),
    )


check_info["couchbase_nodes_cache"] = LegacyCheckDefinition(
    parse_function=parse_couchbase_lines,
    discovery_function=discover_couchbase_nodes_cache,
    check_function=check_couchbase_nodes_cache,
    service_name="Couchbase %s Cache",
    check_ruleset_name="couchbase_cache",
)
