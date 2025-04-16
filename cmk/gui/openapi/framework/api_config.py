#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import enum


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
