#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# LTS release:
# <<<jenkins_version>>>
# 1.23.4
#
# Weekly release:
# <<<jenkins_version>>>
# 1.23

from contextlib import suppress
from typing import NotRequired, TypedDict

import feedparser  # type: ignore[import-untyped]

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

Section = str
Version = tuple[int, int, int]

CHANGELOG_FEED_WEEKLY = "https://www.jenkins.io/changelog/rss.xml"
CHANGELOG_FEED_LTS = "https://www.jenkins.io/changelog-stable/rss.xml"


class ParamsDict(TypedDict):
    diff_state: NotRequired[int]


def parse_jenkins_version(string_table: StringTable) -> Section | None:
    for line in string_table:
        if server_version := line[0].strip():
            return server_version

    return None


def discover_jenkins_version(section: Section) -> DiscoveryResult:
    yield Service()


def check_jenkins_version(
    params: ParamsDict,
    section: Section,
) -> CheckResult:
    """Check the version of the running Jenkins instance

    By default will also try to compare the running version against the latest version available
    as per the release RSS feed.


    >>> list(check_jenkins_version(params={}, section="1.234.5"))[0]
    Result(state=<State.OK: 0>, summary='Version: 1.234.5')
    """
    if not (version_data := section):
        # Let checkmk handle displaying an unknown state
        return

    if (current_version := parse_version(version_data)) is None:
        yield Result(state=State.UNKNOWN, summary=f"Unable to parse version {version_data!r}")
        return

    yield Result(state=State.OK, summary=f"Version: {version_data}")

    # After some internal discussion we always attempt to use the feed
    # and compare versions with each other.
    # If no comparison is desired, please remove the check from the discovery.
    feed_url = CHANGELOG_FEED_LTS if is_lts_release(version_data) else CHANGELOG_FEED_WEEKLY
    feed = feedparser.parse(feed_url)

    if not feed["entries"]:
        message = f"Unable to receive feed data from {feed_url!r}"
        if feed["bozo"] and (bozo_error := feed.get("bozo_exception")):
            message = f"{message}. Exception: {bozo_error}"

        yield Result(state=State.UNKNOWN, notice=message)
        return

    expected_version = None
    for entry in feed["entries"]:
        changelog_link = entry["link"]

        with suppress(ValueError):
            _, latest_version = changelog_link.split("//#v", 1)

            if (expected_version := parse_version(latest_version)) is not None:
                break

    if expected_version is None:
        yield Result(state=State.UNKNOWN, notice="Unable to find a comparable version")
        return

    # We expect to now have a version we can compare with
    if current_version < expected_version:
        yield Result(
            state=State(params.get("diff_state", State.WARN.value)),
            notice=f"Update to {'.'.join(map(str, expected_version))} available",
        )
        yield Result(state=State.OK, summary=f"Changelog: {changelog_link}")


def parse_version(data: str) -> Version | None:
    """
    Create a Jenkins version from a str

    Will return `None` if parsing fails.

    >>> parse_version("1.2.3")
    (1, 2, 3)
    >>> parse_version("4.5")
    (4, 5, 0)
    >>> parse_version("no_version")
    """
    with suppress(ValueError):
        if is_lts_release(version_str=data):
            major, minor, patch = data.split(".", 2)
        else:
            # No patch number on weekly releases, so we supply one
            major, minor, patch = *data.split(".", 1), "0"

        return (int(major), int(minor), int(patch))

    # Unable to determine version. Could be a self-compiled build.
    return None


def is_lts_release(version_str: str) -> bool:
    # Weekly releases use major.minor.
    # LTS releases use major.minor.patch.
    return version_str.count(".") > 1


agent_section_jenkins_version = AgentSection(
    name="jenkins_version",
    parse_function=parse_jenkins_version,
)

check_plugin_jenkins_version = CheckPlugin(
    name="jenkins_version",
    service_name="Jenkins Version",
    discovery_function=discover_jenkins_version,
    check_function=check_jenkins_version,
    check_default_parameters={
        "diff_state": State.WARN.value,
    },
    check_ruleset_name="jenkins_version",
)
