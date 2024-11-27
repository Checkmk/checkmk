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


def discover_couchbase_buckets_vbuckets(section: Section) -> DiscoveryResult:
    yield from (
        (item, {}) for item, data in section.items() if "vb_active_resident_items_ratio" in data
    )


def check_couchbase_buckets_vbuckets(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    resident_items_ratio = data.get("vb_active_resident_items_ratio")
    if resident_items_ratio is not None:
        yield check_levels(
            resident_items_ratio,
            "resident_items_ratio",
            (None, None) + params.get("resident_items_ratio", (None, None)),
            infoname="Resident items ratio",
            human_readable_func=render.percent,
        )

    item_memory = data.get("vb_active_itm_memory")
    if item_memory is not None:
        yield check_levels(
            item_memory,
            "item_memory",
            params.get("item_memory"),
            infoname="Item memory",
            human_readable_func=render.bytes,
        )

    pending_vbuckets = data.get("vb_pending_num")
    if pending_vbuckets is not None:
        yield check_levels(
            int(pending_vbuckets),
            "pending_vbuckets",
            params.get("vb_pending_num"),
            infoname="Pending vBuckets",
            human_readable_func=str,
        )


def check_couchbase_buckets_vbuckets_replica(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    replica_num = data.get("vb_replica_num")
    if replica_num is not None:
        yield check_levels(
            int(replica_num),
            "vbuckets",
            params.get("vb_replica_num"),
            infoname="Total number",
            human_readable_func=str,
        )

    item_memory = data.get("vb_replica_itm_memory")
    if item_memory is not None:
        yield check_levels(
            item_memory,
            "item_memory",
            params.get("item_memory"),
            infoname="Item memory",
            human_readable_func=render.bytes,
        )


check_info["couchbase_buckets_vbuckets"] = LegacyCheckDefinition(
    name="couchbase_buckets_vbuckets",
    parse_function=parse_couchbase_lines,
    service_name="Couchbase Bucket %s active vBuckets",
    discovery_function=discover_couchbase_buckets_vbuckets,
    check_function=check_couchbase_buckets_vbuckets,
    check_ruleset_name="couchbase_vbuckets",
)

check_info["couchbase_buckets_vbuckets.replica"] = LegacyCheckDefinition(
    name="couchbase_buckets_vbuckets_replica",
    service_name="Couchbase Bucket %s replica vBuckets",
    sections=["couchbase_buckets_vbuckets"],
    discovery_function=discover_couchbase_buckets_vbuckets,
    check_function=check_couchbase_buckets_vbuckets_replica,
    check_ruleset_name="couchbase_vbuckets",
)
