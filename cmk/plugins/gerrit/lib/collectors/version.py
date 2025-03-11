#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
import json
from collections.abc import Collection
from typing import Self

import requests

from cmk.utils.semantic_version import SemanticVersion

from cmk.plugins.gerrit.lib.shared_typing import SectionName, Sections


@dataclasses.dataclass
class LatestVersions:
    major: str | None
    minor: str | None
    patch: str | None

    @classmethod
    def build(cls, current: SemanticVersion, versions: Collection[SemanticVersion]) -> Self:
        newer_versions = {v for v in versions if v > current}

        majors = {v for v in newer_versions if v.major > current.major}
        minors = {v for v in newer_versions if v.minor > current.minor} - majors
        patches = {v for v in newer_versions if v.patch > current.patch} - majors - minors

        return cls(
            major=str(max(majors, default="")) or None,
            minor=str(max(minors, default="")) or None,
            patch=str(max(patches, default="")) or None,
        )


class GerritVersion:
    def __init__(self, api_url: str, auth: tuple[str, str]) -> None:
        self.api_url = api_url
        self.auth = auth

    def collect(self) -> Sections:
        current_version = self._get_current_section()
        latest_versions = self._get_latest_versions(current_version)

        return {
            SectionName("version"): {
                "current": str(current_version),
                "latest": dataclasses.asdict(latest_versions),
            },
        }

    def _get_current_section(self) -> SemanticVersion:
        uri = "/config/server/version?verbose"

        resp = requests.get(self.api_url + uri, auth=self.auth, timeout=30)
        resp.raise_for_status()

        clean_content = resp.content.lstrip(b")]}'")  # prefixed with )]}' for security
        data = json.loads(clean_content)

        return SemanticVersion.from_string(data["gerrit_version"])

    @staticmethod
    def _get_latest_versions(current: SemanticVersion) -> LatestVersions:
        gerrit_releases_url = "https://www.googleapis.com/storage/v1/b/gerrit-releases/o"
        query = "?projection=noAcl&fields=items(name)&matchGlob=gerrit-[0-9]*.[0-9]*.[0-9]*.war"

        resp = requests.get(gerrit_releases_url + query, timeout=30)
        resp.raise_for_status()

        versions = {SemanticVersion.from_string(item["name"]) for item in resp.json()["items"]}

        return LatestVersions.build(current, versions)
