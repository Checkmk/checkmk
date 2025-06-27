#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, TypedDict

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

CacheSection = Mapping[str, int | str]

type _Updates = Mapping[Literal["major", "minor", "patch"], str | None]


@dataclass(frozen=True)
class VersionSection:
    current: str
    latest: _Updates | None


def parse_bazel_cache_status(string_table: StringTable) -> CacheSection:
    return {
        key: int(value) if not isinstance(value, str) else value
        for key, value in json.loads(string_table[0][0]).items()
    }


def discover_bazel_cache_status(section: CacheSection) -> DiscoveryResult:
    yield Service()


def check_bazel_cache_status(section: CacheSection) -> CheckResult:
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


class CheckParams(TypedDict):
    major: int
    minor: int
    patch: int


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


def parse_bazel_cache_version(string_table: StringTable) -> VersionSection | None:
    section = {key: value for key, value in json.loads(string_table[0][0]).items()}
    if "current" not in section:
        return None
    return VersionSection(section["current"], section.get("latest"))


agent_section_bazel_cache_version = AgentSection(
    name="bazel_cache_version",
    parse_function=parse_bazel_cache_version,
)


def check_bazel_cache_version(params: CheckParams, section: VersionSection) -> CheckResult:
    yield Result(state=State.OK, summary=f"Current: {section.current}")

    if section.latest is None:
        return

    for release_type, available in section.latest.items():
        yield (
            Result(state=State.OK, notice=f"No new {release_type} release available.")
            if available is None
            else Result(
                state=State(params[release_type]),
                notice=f"Latest {release_type} release: {available}",
            )
        )


check_plugin_bazel_cache_version = CheckPlugin(
    name="bazel_cache_version",
    service_name="Bazel Cache Version",
    check_ruleset_name="bazel_version",
    discovery_function=discover_bazel_cache_status,
    check_function=check_bazel_cache_version,
    check_default_parameters=CheckParams(
        major=State.WARN.value,
        minor=State.WARN.value,
        patch=State.WARN.value,
    ),
)
