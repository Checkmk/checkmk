#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import render
from cmk.plugins.lib.couchbase import parse_couchbase_lines, Section

check_info = {}

DiscoveryResult = Iterable[tuple[str, dict]]


def discover_couchbase_buckets_fragmentation(section: Section) -> DiscoveryResult:
    yield from ((item, {}) for item, data in section.items() if "couch_docs_fragmentation" in data)


def check_couchbase_buckets_fragmentation(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    docs_fragmentation = data.get("couch_docs_fragmentation")
    if docs_fragmentation is not None:
        yield check_levels(
            docs_fragmentation,
            "docs_fragmentation",
            params.get("docs"),
            infoname="Documents fragmentation",
            human_readable_func=render.percent,
        )

    views_fragmentation = data.get("couch_views_fragmentation")
    if views_fragmentation is not None:
        yield check_levels(
            views_fragmentation,
            "views_fragmentation",
            params.get("views"),
            infoname="Views fragmentation",
            human_readable_func=render.percent,
        )


check_info["couchbase_buckets_fragmentation"] = LegacyCheckDefinition(
    name="couchbase_buckets_fragmentation",
    parse_function=parse_couchbase_lines,
    service_name="Couchbase Bucket %s Fragmentation",
    discovery_function=discover_couchbase_buckets_fragmentation,
    check_function=check_couchbase_buckets_fragmentation,
    check_ruleset_name="couchbase_fragmentation",
)
