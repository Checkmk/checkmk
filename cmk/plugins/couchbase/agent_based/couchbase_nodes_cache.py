#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import time
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
    get_rate,
    get_value_store,
    render,
    Service,
)
from cmk.plugins.couchbase.lib import parse_couchbase_lines, Section


def discover_couchbase_nodes_cache(section: Section) -> DiscoveryResult:
    yield from (
        Service(item=item)
        for item, data in section.items()
        if "get_hits" in data and "ep_bg_fetched" in data
    )


def check_couchbase_nodes_cache(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if not (data := section.get(item)):
        return
    misses = data.get("ep_bg_fetched")
    hits = data.get("get_hits")
    if misses is None or hits is None:
        return
    total = misses + hits
    hit_perc = (hits / float(total)) * 100.0 if total != 0 else 100.0
    miss_rate = get_rate(
        get_value_store(), "cache_misses", time.time(), misses, raise_overflow=True
    )

    yield from check_levels(
        miss_rate,
        "cache_misses_rate",
        params.get("cache_misses"),
        human_readable_func=lambda x: f"{x}/s",
        infoname="Cache misses",
    )

    yield from check_levels(
        hit_perc,
        "cache_hit_ratio",
        (None, None) + params.get("cache_hits", (None, None)),
        human_readable_func=render.percent,
        infoname="Cache hits",
        boundaries=(0, 100),
    )


agent_section_couchbase_nodes_cache = AgentSection(
    name="couchbase_nodes_cache",
    parse_function=parse_couchbase_lines,
)


check_plugin_couchbase_nodes_cache = CheckPlugin(
    name="couchbase_nodes_cache",
    service_name="Couchbase %s Cache",
    discovery_function=discover_couchbase_nodes_cache,
    check_function=check_couchbase_nodes_cache,
    check_ruleset_name="couchbase_cache",
    check_default_parameters={},
)
