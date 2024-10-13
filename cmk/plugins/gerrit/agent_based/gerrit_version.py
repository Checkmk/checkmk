#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal, TypedDict

import pydantic

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


class LatestVersions(TypedDict):
    """Mapping of the latest available Gerrit version by release type."""

    major: str | None
    minor: str | None
    patch: str | None


class VersionInfo(pydantic.BaseModel):
    """Version information related to deployed Gerrit instance."""

    model_config = pydantic.ConfigDict(frozen=True)

    current: str
    """The current version of deployed Gerrit instance."""
    latest: LatestVersions
    """The latest available major, minor and patch Gerrit release."""


def parse_gerrit_version(string_table: StringTable) -> VersionInfo | None:
    """Parse Gerrit version from agent output."""
    match string_table:
        case [[payload]]:
            return VersionInfo.model_validate_json(payload)
        case _:
            return None


def discover_gerrit_version(section: VersionInfo | None) -> DiscoveryResult:
    """Runs empty discovery since there is only a single service."""
    yield Service()


class CheckParams(TypedDict):
    """Parameters passed to plugin via ruleset (see defaults)."""

    major: int
    minor: int
    patch: int


ReleaseType = Literal["major", "minor", "patch"]
"""Release types based on semantic versioning."""


def get_changelog_url(release: str, release_type: ReleaseType) -> str:
    """Build Gerrit changelog url for a given release."""
    major, minor, patch = release.split(".")
    base_url = f"https://www.gerritcodereview.com/{major}.{minor}.html"

    match release_type:
        case "major" | "minor":
            return base_url
        case "patch":
            return f"{base_url}#{major}{minor}{patch}"


def get_latest_version_notice(
    params: CheckParams, latest_versions: LatestVersions, release_type: ReleaseType
) -> Result:
    """Build result notice based on whether there's an available version update."""
    if (latest := latest_versions[release_type]) is None:
        return Result(state=State.OK, notice=f"No new {release_type} release available.")

    changelog_url = get_changelog_url(latest, release_type)

    return Result(
        state=State(params[release_type]),
        notice=f"Latest {release_type} release: {latest} {changelog_url} ",
    )


def check_gerrit_version(params: CheckParams, section: VersionInfo | None) -> CheckResult:
    """Checks the Gerrit version section returning valid checkmk results."""
    if not section:
        return

    yield Result(state=State.OK, summary=f"Current: {section.current}")

    yield get_latest_version_notice(params, section.latest, "major")
    yield get_latest_version_notice(params, section.latest, "minor")
    yield get_latest_version_notice(params, section.latest, "patch")


agent_section_gerrit_version = AgentSection(
    name="gerrit_version",
    parse_function=parse_gerrit_version,
)

check_plugin_gerrit_version = CheckPlugin(
    name="gerrit_version",
    service_name="Gerrit Version",
    discovery_function=discover_gerrit_version,
    check_function=check_gerrit_version,
    check_ruleset_name="gerrit_version",
    check_default_parameters=CheckParams(
        major=State.WARN.value,
        minor=State.WARN.value,
        patch=State.WARN.value,
    ),
)
