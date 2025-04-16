#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import enum
from collections.abc import Mapping, Sequence
from typing import TypedDict


class DeprecationDetails(TypedDict):
    warning_message: str
    removal_date: str


class APIVersion(enum.Enum):
    """API versions supported by the application"""

    V1 = "v1"
    UNSTABLE = "unstable"

    @staticmethod
    def from_string(api_version_string: str) -> "APIVersion":
        return APIVersion(api_version_string)

    @property
    def numeric_value(self) -> int:
        if self.value.startswith("v") and self.value[1:].isdigit():
            return int(self.value[1:])

        # unstable versions are considered higher than any stable version
        return 999

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, APIVersion):
            return NotImplemented
        return self.numeric_value < other.numeric_value

    def __le__(self, other: object) -> bool:
        if not isinstance(other, APIVersion):
            return NotImplemented
        return self.numeric_value <= other.numeric_value


class APIConfig:
    """Configuration for the versioned API system"""

    RELEASED_VERSIONS_IN_ORDER = [
        APIVersion.V1,  # Legacy version (includes all marshmallow endpoints)
    ]

    DEVELOPMENT_VERSIONS: Sequence[APIVersion] = []

    DEPRECATED_VERSIONS: Mapping[APIVersion, DeprecationDetails] = {}

    @classmethod
    def is_version_available(cls, version: APIVersion, development_mode: bool = False) -> bool:
        """Check if a version is available in the current environment"""
        if version in cls.RELEASED_VERSIONS_IN_ORDER:
            return True

        if development_mode and version in cls.DEVELOPMENT_VERSIONS:
            return True

        return False

    @classmethod
    def is_version_deprecated(cls, version: APIVersion) -> bool:
        """Check if a version is deprecated"""
        return version in cls.DEPRECATED_VERSIONS

    @classmethod
    def get_released_versions(
        cls, from_version: APIVersion | None = None, to_version: APIVersion | None = None
    ) -> Sequence[APIVersion]:
        """Get all released versions between two versions"""

        if from_version is None and to_version is None:
            return cls.RELEASED_VERSIONS_IN_ORDER

        versions = []
        if from_version is None:
            from_version = cls.RELEASED_VERSIONS_IN_ORDER[0]

        if to_version is None:
            to_version = cls.RELEASED_VERSIONS_IN_ORDER[-1]

        for version in cls.RELEASED_VERSIONS_IN_ORDER:
            if from_version <= version <= to_version:
                versions.append(version)

        return versions
