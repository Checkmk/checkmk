#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable

from cmk.base.check_api import check_levels, get_bytes_human_readable, LegacyCheckDefinition
from cmk.base.check_legacy_includes.mem import check_memory_element
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.utils.couchbase import parse_couchbase_lines, Section

DiscoveryResult = Iterable[tuple[str, dict]]


def discover_couchbase_buckets_mem(section: Section) -> DiscoveryResult:
    yield from (
        (item, {}) for item, data in section.items() if "mem_total" in data and "mem_free" in data
    )


def check_couchbase_bucket_mem(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    warn, crit = params.get("levels", (None, None))
    mode = "abs_used" if isinstance(warn, int) else "perc_used"
    try:
        yield check_memory_element(
            "Usage",
            data["mem_total"] - data["mem_free"],
            data["mem_total"],
            (mode, (warn, crit)),
            metric_name="memused_couchbase_bucket",
        )
    except (KeyError, TypeError):
        pass

    low_watermark = data.get("ep_mem_low_wat")
    if low_watermark is not None:
        yield check_levels(
            low_watermark,
            "mem_low_wat",
            None,
            infoname="Low watermark",
            human_readable_func=get_bytes_human_readable,
        )

    high_watermark = data.get("ep_mem_high_wat")
    if high_watermark is not None:
        yield check_levels(
            high_watermark,
            "mem_high_wat",
            None,
            infoname="High watermark",
            human_readable_func=get_bytes_human_readable,
        )


check_info["couchbase_buckets_mem"] = LegacyCheckDefinition(
    parse_function=parse_couchbase_lines,
    discovery_function=discover_couchbase_buckets_mem,
    check_function=check_couchbase_bucket_mem,
    service_name="Couchbase Bucket %s Memory",
    check_ruleset_name="memory_multiitem",
)
