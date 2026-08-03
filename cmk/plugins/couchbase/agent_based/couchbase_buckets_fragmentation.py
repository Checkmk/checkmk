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


def discover_couchbase_buckets_fragmentation(section: Section) -> DiscoveryResult:
    yield from (
        Service(item=item) for item, data in section.items() if "couch_docs_fragmentation" in data
    )


def check_couchbase_buckets_fragmentation(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if not (data := section.get(item)):
        return
    docs_fragmentation = data.get("couch_docs_fragmentation")
    if docs_fragmentation is not None:
        yield from check_levels(
            docs_fragmentation,
            "docs_fragmentation",
            params.get("docs"),
            infoname="Documents fragmentation",
            human_readable_func=render.percent,
        )

    views_fragmentation = data.get("couch_views_fragmentation")
    if views_fragmentation is not None:
        yield from check_levels(
            views_fragmentation,
            "views_fragmentation",
            params.get("views"),
            infoname="Views fragmentation",
            human_readable_func=render.percent,
        )


agent_section_couchbase_buckets_fragmentation = AgentSection(
    name="couchbase_buckets_fragmentation",
    parse_function=parse_couchbase_lines,
)


check_plugin_couchbase_buckets_fragmentation = CheckPlugin(
    name="couchbase_buckets_fragmentation",
    service_name="Couchbase Bucket %s Fragmentation",
    discovery_function=discover_couchbase_buckets_fragmentation,
    check_function=check_couchbase_buckets_fragmentation,
    check_ruleset_name="couchbase_fragmentation",
    check_default_parameters={},
)
