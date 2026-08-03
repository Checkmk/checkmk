#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import contextlib
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
from cmk.plugins.lib.memory import check_element


def discover_couchbase_buckets_mem(section: Section) -> DiscoveryResult:
    yield from (
        Service(item=item)
        for item, data in section.items()
        if "mem_total" in data and "mem_free" in data
    )


def check_couchbase_bucket_mem(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if not (data := section.get(item)):
        return
    levels = params.get("levels")
    mode = "abs_used" if isinstance(levels, tuple) and isinstance(levels[0], int) else "perc_used"
    with contextlib.suppress(KeyError, TypeError):
        yield from check_element(
            "Usage",
            data["mem_total"] - data["mem_free"],
            data["mem_total"],
            (mode, levels),  # type: ignore[arg-type]
            metric_name="memused_couchbase_bucket",
        )

    low_watermark = data.get("ep_mem_low_wat")
    if low_watermark is not None:
        yield from check_levels(
            low_watermark,
            "mem_low_wat",
            None,
            infoname="Low watermark",
            human_readable_func=render.bytes,
        )

    high_watermark = data.get("ep_mem_high_wat")
    if high_watermark is not None:
        yield from check_levels(
            high_watermark,
            "mem_high_wat",
            None,
            infoname="High watermark",
            human_readable_func=render.bytes,
        )


agent_section_couchbase_buckets_mem = AgentSection(
    name="couchbase_buckets_mem",
    parse_function=parse_couchbase_lines,
)


check_plugin_couchbase_buckets_mem = CheckPlugin(
    name="couchbase_buckets_mem",
    service_name="Couchbase Bucket %s Memory",
    discovery_function=discover_couchbase_buckets_mem,
    check_function=check_couchbase_bucket_mem,
    check_ruleset_name="memory_multiitem",
    check_default_parameters={"levels": None},
)
