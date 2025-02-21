#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
import json
from collections.abc import Collection
from typing import Protocol, Self

import requests

from cmk.utils.semantic_version import SemanticVersion

from cmk.plugins.gerrit.lib.shared_typing import SectionName, Sections


class SectionCollector(Protocol):
    def collect(self) -> Sections: ...


def collect_sections(collector: SectionCollector) -> Sections:
    return collector.collect()


@dataclasses.dataclass
class LatestVersions:
    major: str | None
    minor: str | None
    patch: str | None

    @classmethod
    def build(cls, current: SemanticVersion, versions: Collection[SemanticVersion]) -> Self:
        return cls(
            major=str(max((v for v in versions if v.major > current.major), default="")) or None,
            minor=str(max((v for v in versions if v.minor > current.minor), default="")) or None,
            patch=str(max((v for v in versions if v.patch > current.patch), default="")) or None,
        )


class SyncSectionCollector:
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
