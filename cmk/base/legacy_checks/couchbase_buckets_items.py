#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.plugins.lib.couchbase import parse_couchbase_lines, Section

check_info = {}

DiscoveryResult = Iterable[tuple[str, dict]]


def discover_couchbase_buckets_items(section: Section) -> DiscoveryResult:
    yield from ((item, {}) for item, data in section.items() if "curr_items_tot" in data)


def check_couchbase_buckets_items(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    total_items = data.get("curr_items_tot")
    if total_items is not None:
        yield check_levels(
            int(total_items),
            "items_count",
            params.get("curr_items_tot"),
            infoname="Total items in vBuckets",
            human_readable_func=str,
        )

    write_queue = data.get("disk_write_queue")
    if write_queue is not None:
        yield check_levels(
            int(write_queue),
            "disk_write_ql",
            params.get("disk_write_ql"),
            infoname="Items in disk write queue",
            human_readable_func=str,
        )

    fetched = data.get("ep_bg_fetched")
    if fetched is not None:
        yield check_levels(
            int(fetched),
            "fetched_items",
            params.get("fetched_items"),
            infoname="Items fetched from disk",
            human_readable_func=str,
        )

    queue_fill = data.get("ep_diskqueue_fill")
    if queue_fill is not None:
        yield check_levels(
            queue_fill,
            "disk_fill_rate",
            params.get("disk_fill_rate"),
            unit="/s",
            infoname="Disk queue fill rate",
        )

    queue_drain = data.get("ep_diskqueue_drain")
    if queue_drain is not None:
        yield check_levels(
            queue_drain,
            "disk_drain_rate",
            params.get("disk_drain_rate"),
            unit="/s",
            infoname="Disk queue drain rate",
        )


check_info["couchbase_buckets_items"] = LegacyCheckDefinition(
    name="couchbase_buckets_items",
    parse_function=parse_couchbase_lines,
    service_name="Couchbase Bucket %s Items",
    discovery_function=discover_couchbase_buckets_items,
    check_function=check_couchbase_buckets_items,
    check_ruleset_name="couchbase_items",
)
