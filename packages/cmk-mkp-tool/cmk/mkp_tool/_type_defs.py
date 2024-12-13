#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import re
from collections.abc import Iterable
from functools import cached_property
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, field_validator, GetCoreSchemaHandler
from pydantic_core import core_schema


class PackageError(Exception):
    pass


_SortKeyElement = (
    # First element makes sure
    #  a) Never compare different types
    #  b) Numeric identifiers always have lower precedence than non-numeric identifiers
    #  c) A larger set of fields has a higher precedence than a smaller set,
    #     if all of the preceding identifiers are equal.
    tuple[Literal[0], str] | tuple[Literal[1], int] | tuple[Literal[2], None]
)


class PackageVersion(str):
    # one fine day we might remove the inheritance, but for now this'll have to do.
    _MISMATCH_MSG = "Invalid version %r. A package version must not contain slashes"

    # semver pattern according to semver.org
    # Watch out, currently matching this pattern is *not* a requirement
    # for becoming a PackageVersion (but it should be in the future).
    _SEMVER_PATTERN = re.compile(
        # major
        r"^(?P<major>0|[1-9]\d*)"
        # minor
        r"\.(?P<minor>0|[1-9]\d*)"
        # patch
        r"\.(?P<patch>0|[1-9]\d*)"
        # prerelease
        r"(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
        r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
        # build metadata
        r"(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
    )

    def __new__(cls, value: str) -> PackageVersion:
        if "/" in value:
            raise ValueError(cls._MISMATCH_MSG % value)
        return super().__new__(cls, value)

    @classmethod
    def validate(cls, value: str | PackageVersion) -> PackageVersion:
        return cls(value)

    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: object, _handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls.validate, core_schema.str_schema(), serialization=core_schema.to_string_ser_schema()
        )

    @classmethod
    def parse_semver(cls, raw: str) -> Self:
        if cls._SEMVER_PATTERN.match(raw):
            return cls(raw)
        raise ValueError(f"Not a valid semantic versioning string: {raw!r}")

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
        "Invalid name %r. A package name must only consist of letters, digits, dash and "
        "underscore and it must start with a letter or underscore."
    )

    @classmethod
    def validate(cls, value: str | PackageName) -> PackageName:
        return cls(value)

    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: object, _handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls.validate, core_schema.str_schema(), serialization=core_schema.to_string_ser_schema()
        )

    def __new__(cls, value: str) -> PackageName:
        if not cls._REGEX.match(value):
            raise ValueError(cls._MISMATCH_MSG % value)
        return super().__new__(cls, value)


class PackageID(BaseModel):
    # FIXME: implement `__get_pydantic_core_schema__` on your custom type to fully support it.
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        frozen=True,
    )

    name: PackageName
    version: PackageVersion

    @field_validator("name")
    def make_name(cls, value: str) -> PackageName:
        return PackageName(value)

    @field_validator("version")
    def make_version(cls, value: str) -> PackageVersion:
        return PackageVersion(value)
