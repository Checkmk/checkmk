#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    State,
    StringTable,
)

Section = Mapping[str, int | str]


def parse_bazel_cache_status(string_table: StringTable) -> Section:
    return {
        key: int(value) if not isinstance(value, str) else value
        for key, value in json.loads(string_table[0][0]).items()
    }


def discover_bazel_cache_status(section: Section) -> DiscoveryResult:
    yield Service()


def check_bazel_cache_status(section: Section) -> CheckResult:
    if not section:
        yield Result(state=State.UNKNOWN, summary="No Bazel Cache Status")
        return

    yield Result(state=State.OK, summary="Bazel Cache Status is OK")

    metric_name_prefix = "bazel_cache_status_"

    yield from check_levels(
        int(section["curr_size"]),
        metric_name=f"{metric_name_prefix}curr_size",
        render_func=render.bytes,
        label="Current size",
    )
    yield from check_levels(
        int(section["max_size"]),
        label="Maximum size",
        metric_name=f"{metric_name_prefix}max_size",
        render_func=render.bytes,
    )
    yield from check_levels(
        int(section["num_files"]),
        label="Number of files",
        metric_name=f"{metric_name_prefix}num_files",
        render_func=str,
    )
    yield from check_levels(
        int(section["num_goroutines"]),
        label="Number of Go routines",
        metric_name=f"{metric_name_prefix}num_goroutines",
        render_func=str,
    )
    yield from check_levels(
        int(section["reserved_size"]),
        label="Reserved size",
        metric_name=f"{metric_name_prefix}reserved_size",
        render_func=render.bytes,
    )
    yield from check_levels(
        int(section["uncompressed_size"]),
        label="Uncompressed size",
        metric_name=f"{metric_name_prefix}uncompressed_size",
        render_func=render.bytes,
    )


agent_section_bazel_cache_status = AgentSection(
    name="bazel_cache_status",
    parse_function=parse_bazel_cache_status,
)

check_plugin_bazel_cache_status = CheckPlugin(
    name="bazel_cache_status",
    service_name="Bazel Cache Status",
    discovery_function=discover_bazel_cache_status,
    check_function=check_bazel_cache_status,
)
