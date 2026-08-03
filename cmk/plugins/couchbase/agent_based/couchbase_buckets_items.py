#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.legacy.conversion import (
    # Temporary compatibility layer untile we migrate the corresponding ruleset.
    check_levels_legacy_compatible as check_levels,
)
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
)
from cmk.plugins.couchbase.lib import parse_couchbase_lines, Section


def discover_couchbase_buckets_items(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item, data in section.items() if "curr_items_tot" in data)


def check_couchbase_buckets_items(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if not (data := section.get(item)):
        return
    total_items = data.get("curr_items_tot")
    if total_items is not None:
        yield from check_levels(
            int(total_items),
            "items_count",
            params.get("curr_items_tot"),
            infoname="Total items in vBuckets",
            human_readable_func=str,
        )

    write_queue = data.get("disk_write_queue")
    if write_queue is not None:
        yield from check_levels(
            int(write_queue),
            "disk_write_ql",
            params.get("disk_write_ql"),
            infoname="Items in disk write queue",
            human_readable_func=str,
        )

    fetched = data.get("ep_bg_fetched")
    if fetched is not None:
        yield from check_levels(
            int(fetched),
            "fetched_items",
            params.get("fetched_items"),
            infoname="Items fetched from disk",
            human_readable_func=str,
        )

    queue_fill = data.get("ep_diskqueue_fill")
    if queue_fill is not None:
        yield from check_levels(
            queue_fill,
            "disk_fill_rate",
            params.get("disk_fill_rate"),
            human_readable_func=lambda x: f"{x:.2f}/s",
            infoname="Disk queue fill rate",
        )

    queue_drain = data.get("ep_diskqueue_drain")
    if queue_drain is not None:
        yield from check_levels(
            queue_drain,
            "disk_drain_rate",
            params.get("disk_drain_rate"),
            human_readable_func=lambda x: f"{x:.2f}/s",
            infoname="Disk queue drain rate",
        )


agent_section_couchbase_buckets_items = AgentSection(
    name="couchbase_buckets_items",
    parse_function=parse_couchbase_lines,
)


check_plugin_couchbase_buckets_items = CheckPlugin(
    name="couchbase_buckets_items",
    service_name="Couchbase Bucket %s Items",
    discovery_function=discover_couchbase_buckets_items,
    check_function=check_couchbase_buckets_items,
    check_ruleset_name="couchbase_items",
    check_default_parameters={},
)
