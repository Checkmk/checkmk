#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.gerrit.lib.collectors.version import LatestVersions
from cmk.utils.semantic_version import SemanticVersion

_AVAILABLE_GERRIT_VERSIONS = (
    "4.0.0",
    "3.11.1",
    "3.11.0",
    "3.10.4",
    "3.10.3",
    "3.10.2",
    "3.10.1",
    "3.10.0",
)


def test_latest_versions_current_version_is_already_the_latest() -> None:
    current_version = "4.0.0"
    available_versions = [SemanticVersion.from_string(v) for v in _AVAILABLE_GERRIT_VERSIONS]

    value = LatestVersions.build(SemanticVersion.from_string(current_version), available_versions)
    expected = LatestVersions(major=None, minor=None, patch=None)

    assert value == expected


def test_latest_versions_is_when_newer_versions_are_available() -> None:
    current_version = "3.10.1"
    available_versions = [SemanticVersion.from_string(v) for v in _AVAILABLE_GERRIT_VERSIONS]

    value = LatestVersions.build(SemanticVersion.from_string(current_version), available_versions)
    expected = LatestVersions(major="4.0.0", minor="3.11.1", patch="3.10.4")

    assert value == expected
