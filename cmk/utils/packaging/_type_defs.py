#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import re
from collections.abc import Iterable
from functools import cached_property
from typing import Literal, Union

from pydantic import BaseModel
from semver import VersionInfo

from cmk.utils.exceptions import MKException


class PackageException(MKException):
    pass


_SortKeyElement = Union[
    # First element makes sure
    #  a) Never compare different types
    #  b) Numeric identifiers always have lower precedence than non-numeric identifiers
    #  c) A larger set of fields has a higher precedence than a smaller set, if all of the preceding identifiers are equal.
    tuple[Literal[0], str],
    tuple[Literal[1], int],
    tuple[Literal[2], None],
]


class PackageVersion(str):
    # one fine day we might remove the inheritance, but for now this'll have to do.

    @staticmethod
    def parse_semver(raw: str) -> VersionInfo:
        return VersionInfo.parse(raw)

    @cached_property
    def sort_key(self) -> tuple[_SortKeyElement, ...]:
        """Try our best to sort version strings

        This should be compatible with the spec for semantic versioning (semver.org).
        """

        def convert_identifiers(ids: str) -> Iterable[_SortKeyElement]:
            for i in ids.split("."):
                try:
                    yield (1, int(i))
                except ValueError:
                    yield (0, i)

        without_build_metadata = self.split("+", 1)[0]

        version, prerelease = (
            without_build_metadata.split("-", 1)
            if "-" in without_build_metadata
            else (without_build_metadata, "")
        )
        return (
            tuple(convert_identifiers(version))
            + (tuple(convert_identifiers(prerelease)) if prerelease else ())
            + ((2, None),)
        )


class PackageName(str):
    _REGEX = re.compile(r"^[^\d\W][-\w]*$")
    _MISMATCH_MSG = (
        "A package name must only consist of letters, digits, dash and "
        "underscore and it must start with a letter or underscore."
    )

    def __new__(cls, value: str) -> PackageName:
        if not cls._REGEX.match(value):
            raise ValueError(cls._MISMATCH_MSG)
        return super().__new__(cls, value)


class PackageID(BaseModel, frozen=True):
    name: PackageName
    version: PackageVersion
