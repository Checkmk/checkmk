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


def discover_couchbase_buckets_cache(section: Section) -> DiscoveryResult:
    yield from (
        Service(item=item) for item, data in section.items() if "ep_cache_miss_rate" in data
    )


def check_couchbase_buckets_cache(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if not (data := section.get(item)):
        return
    miss_rate = data.get("ep_cache_miss_rate")
    if miss_rate is not None:
        yield from check_levels(
            miss_rate,
            "cache_misses_rate",
            params.get("cache_misses"),
            human_readable_func=lambda x: f"{x}/s",
            infoname="Cache misses",
        )


agent_section_couchbase_buckets_cache = AgentSection(
    name="couchbase_buckets_cache",
    parse_function=parse_couchbase_lines,
)


check_plugin_couchbase_buckets_cache = CheckPlugin(
    name="couchbase_buckets_cache",
    service_name="Couchbase Bucket %s Cache",
    discovery_function=discover_couchbase_buckets_cache,
    check_function=check_couchbase_buckets_cache,
    check_ruleset_name="couchbase_cache",
    check_default_parameters={},
)
