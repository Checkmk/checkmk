#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
import re
from typing import Self


@dataclasses.dataclass(frozen=True, slots=True, order=True)
class SemanticVersion:
    """Container that represents a semantic version (https://semver.org)."""

    major: int
    """Major release with incompatible API changes."""
    minor: int
    """Minor release with backwards compatible features."""
    patch: int
    """Patch release with backwards compatible bug fixes."""

    def __str__(self) -> str:
        """Format the semantic version into a string."""
        return f"{self.major}.{self.minor}.{self.patch}"

    @classmethod
    def from_string(cls, string: str) -> Self:
        """
        Build semantic version from raw string via regex pattern matching.

        >>> SemanticVersion.from_string("2.0.1")
        SemanticVersion(major=2, minor=0, patch=1)

        """
        if not (match := re.compile(r"\d+.\d+.\d+").search(string)):
            raise ValueError(f"No semantic version detected in string: {string!r}.")

        major, minor, patch = match.group().split(".")

        return cls(int(major), int(minor), int(patch))
