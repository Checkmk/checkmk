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
    render,
    Service,
)
from cmk.plugins.couchbase.lib import parse_couchbase_lines, Section


def discover_couchbase_buckets_vbuckets(section: Section) -> DiscoveryResult:
    yield from (
        Service(item=item)
        for item, data in section.items()
        if "vb_active_resident_items_ratio" in data
    )


def check_couchbase_buckets_vbuckets(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if not (data := section.get(item)):
        return
    resident_items_ratio = data.get("vb_active_resident_items_ratio")
    if resident_items_ratio is not None:
        yield from check_levels(
            resident_items_ratio,
            "resident_items_ratio",
            (None, None) + params.get("resident_items_ratio", (None, None)),
            infoname="Resident items ratio",
            human_readable_func=render.percent,
        )

    item_memory = data.get("vb_active_itm_memory")
    if item_memory is not None:
        yield from check_levels(
            item_memory,
            "item_memory",
            params.get("item_memory"),
            infoname="Item memory",
            human_readable_func=render.bytes,
        )

    pending_vbuckets = data.get("vb_pending_num")
    if pending_vbuckets is not None:
        yield from check_levels(
            int(pending_vbuckets),
            "pending_vbuckets",
            params.get("vb_pending_num"),
            infoname="Pending vBuckets",
            human_readable_func=str,
        )


def check_couchbase_buckets_vbuckets_replica(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if not (data := section.get(item)):
        return
    replica_num = data.get("vb_replica_num")
    if replica_num is not None:
        yield from check_levels(
            int(replica_num),
            "vbuckets",
            params.get("vb_replica_num"),
            infoname="Total number",
            human_readable_func=str,
        )

    item_memory = data.get("vb_replica_itm_memory")
    if item_memory is not None:
        yield from check_levels(
            item_memory,
            "item_memory",
            params.get("item_memory"),
            infoname="Item memory",
            human_readable_func=render.bytes,
        )


agent_section_couchbase_buckets_vbuckets = AgentSection(
    name="couchbase_buckets_vbuckets",
    parse_function=parse_couchbase_lines,
)


check_plugin_couchbase_buckets_vbuckets = CheckPlugin(
    name="couchbase_buckets_vbuckets",
    service_name="Couchbase Bucket %s active vBuckets",
    discovery_function=discover_couchbase_buckets_vbuckets,
    check_function=check_couchbase_buckets_vbuckets,
    check_ruleset_name="couchbase_vbuckets",
    check_default_parameters={},
)


check_plugin_couchbase_buckets_vbuckets_replica = CheckPlugin(
    name="couchbase_buckets_vbuckets_replica",
    service_name="Couchbase Bucket %s replica vBuckets",
    sections=["couchbase_buckets_vbuckets"],
    discovery_function=discover_couchbase_buckets_vbuckets,
    check_function=check_couchbase_buckets_vbuckets_replica,
    check_ruleset_name="couchbase_vbuckets",
    check_default_parameters={},
)
