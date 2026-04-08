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
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)


@dataclass(frozen=True)
class VersionSection:
    current: str
    latest: Mapping[Literal["major", "minor", "patch"], str | None] | None


def parse_bazel_cache_version(string_table: StringTable) -> VersionSection | None:
    section = {key: value for key, value in json.loads(string_table[0][0]).items()}
    if "current" not in section:
        return None
    return VersionSection(section["current"], section.get("latest"))


def discover_bazel_cache_version(section: VersionSection) -> DiscoveryResult:
    yield Service()


agent_section_bazel_cache_version = AgentSection(
    name="bazel_cache_version",
    parse_function=parse_bazel_cache_version,
)


class CheckParams(TypedDict):
    major: int
    minor: int
    patch: int


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
    discovery_function=discover_bazel_cache_version,
    check_function=check_bazel_cache_version,
    check_default_parameters=CheckParams(
        major=State.WARN.value,
        minor=State.WARN.value,
        patch=State.WARN.value,
    ),
)
